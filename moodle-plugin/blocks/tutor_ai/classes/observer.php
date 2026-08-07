<?php
defined('MOODLE_INTERNAL') || die();

class block_tutor_ai_observer {

    public static function course_module_created(\core\event\course_module_created $event) {

        $data = $event->get_data();

        // Seulement les ressources fichier
        if ($data['other']['modulename'] !== 'resource') {
            return;
        }

        $courseid   = $data['courseid'];
        $resourceid = $data['objectid'];

        // Recuperation du module
        $cm = get_coursemodule_from_id('resource', $resourceid);
        if (!$cm) {
            return;
        }

        // Contexte du module
        $context = context_module::instance($cm->id);

        // Recuperation du fichier uploade
        $fs    = get_file_storage();
        $files = $fs->get_area_files(
            $context->id,
            'mod_resource',
            'content',
            0,
            'filename',
            false
        );

        if (empty($files)) {
            return;
        }

        $file      = reset($files);
        $filename  = $file->get_filename();
        $extension = strtolower(pathinfo($filename, PATHINFO_EXTENSION));

        // Formats supportes par document_extractor.py
        $allowed       = ['pdf', 'docx', 'pptx', 'txt'];
        $resource_type = in_array($extension, $allowed) ? $extension : 'pdf';

        // Token Moodle pour acces authentifie aux fichiers
        $token = '9b51850beb895796c784a7b8dd805d00';

        // URL authentifiee du fichier via webservice/pluginfile.php
        $file_url =
    'http://host.docker.internal:8082/webservice/tokenpluginfile.php/'
    . $token . '/'
    . $context->id
    . '/mod_resource/content/0/'
    . rawurlencode($filename);

        $payload = json_encode([
            'course_id'     => (int) $courseid,
            'resource_id'   => (int) $resourceid,
            'resource_type' => $resource_type,
            'file_url'      => $file_url
        ]);

        // Appel HTTP POST vers le microservice FastAPI
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