<?php
defined('MOODLE_INTERNAL') || die();

class block_tutor_ai_observer {

    /**
     * Observateur déclenché à la création d'un module de cours dans Moodle.
     *
     * Filtre les modules supportés (resource, assign, folder, page, book),
     * récupère les fichiers attachés via l'API Moodle File Storage,
     * et envoie chaque fichier PDF/DOCX/PPTX/TXT au service FastAPI
     * via une requête HTTP POST cURL vers /upload-resource.
     *
     * Flux complet :
     * 1. Vérification que le module est dans la liste supportée.
     * 2. Résolution du course module ($cm) via get_coursemodule_from_id.
     * 3. Récupération du contexte Moodle (context_module::instance).
     * 4. Lecture des fichiers dans la filearea correspondante au type de module.
     * 5. Filtrage par extension (pdf, docx, pptx, txt).
     * 6. Lecture du token d'authentification webservice depuis external_tokens
     *    (service shortname : "edora_ai").
     * 7. Construction de l'URL authentifiée pluginfile.php avec le token.
     * 8. Envoi POST JSON vers http://host.docker.internal:8000/upload-resource
     *    avec {course_id, resource_id, resource_type, file_url}.
     *
     * @param \core\event\course_module_created $event Événement Moodle de création de module.
     * @return void  Retourne silencieusement si le module n'est pas supporté,
     *               si aucun fichier éligible n'est trouvé, ou si le token est absent.
     */
    public static function course_module_created(\core\event\course_module_created $event): void {
        $data = $event->get_data();
        $modulename = $data['other']['modulename'];

        // Modules supportés
        $supported_modules = ['resource', 'assign', 'folder', 'page', 'book'];
        if (!in_array($modulename, $supported_modules)) {
            return;
        }

        $courseid   = $data['courseid'];
        $resourceid = $data['objectid'];

        // Mapping module → component + filearea
        $module_config = [
            'resource' => ['component' => 'mod_resource', 'filearea' => 'content',         'itemid' => 0],
            'assign'   => ['component' => 'mod_assign',   'filearea' => 'introattachment', 'itemid' => 0],
            'folder'   => ['component' => 'mod_folder',   'filearea' => 'content',         'itemid' => 0],
            'page'     => ['component' => 'mod_page',     'filearea' => 'content',         'itemid' => 0],
            'book'     => ['component' => 'mod_book',     'filearea' => 'chapter',         'itemid' => null],
        ];
        $config = $module_config[$modulename];

        // Récupération du module
        $cm = get_coursemodule_from_id($modulename, $resourceid);
        if (!$cm) {
            return;
        }

        // Contexte du module
        $context = context_module::instance($cm->id);

        // Récupération des fichiers
        $fs    = get_file_storage();
        $files = $fs->get_area_files(
            $context->id,
            $config['component'],
            $config['filearea'],
            $config['itemid'] !== null ? $config['itemid'] : false,
            'filename',
            false
        );

        if (empty($files)) {
            return;
        }

        $allowed = ['pdf', 'docx', 'pptx', 'txt'];

        foreach ($files as $file) {
            $filename  = $file->get_filename();
            $extension = strtolower(pathinfo($filename, PATHINFO_EXTENSION));

            if (!in_array($extension, $allowed)) {
                continue;
            }

            $resource_type = $extension;

            // Token lu depuis la DB
            global $DB;
            $token_record = $DB->get_record('external_tokens', ['externalserviceid' =>
                $DB->get_field('external_services', 'id', ['shortname' => 'edora_ai'])
            ]);
            if (!$token_record) {
                return;
            }
            $token = $token_record->token;

            // URL authentifiée
            $file_url =
                'http://host.docker.internal:8082/webservice/pluginfile.php/'
                . $context->id . '/'
                . $config['component'] . '/'
                . $config['filearea'] . '/'
                . $file->get_itemid() . '/'
                . rawurlencode($filename)
                . '?token=' . $token;

            $payload = json_encode([
                'course_id'     => (int) $courseid,
                'resource_id'   => (int) $resourceid,
                'resource_type' => $resource_type,
                'file_url'      => $file_url,
            ]);

            // Appel HTTP POST vers FastAPI
            $ch = curl_init('http://host.docker.internal:8000/upload-resource');
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_POST,           true);
            curl_setopt($ch, CURLOPT_POSTFIELDS,     $payload);
            curl_setopt($ch, CURLOPT_HTTPHEADER,     ['Content-Type: application/json']);
            curl_setopt($ch, CURLOPT_TIMEOUT,        10);
            curl_exec($ch);
            curl_close($ch);
        }
    }
}