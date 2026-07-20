<?php
defined('MOODLE_INTERNAL') || die();

class block_tutor_ai_observer {

    public static function course_module_created(\core\event\course_module_created $event) {
        $data = $event->get_data();
        
        // Seulement pour les ressources de type fichier
        if ($data['other']['modulename'] !== 'resource') {
            return;
        }

        $course_id   = $data['courseid'];
        $resource_id = $data['objectid'];

        // Appel HTTP vers le microservice FastAPI
        $url = 'http://host.docker.internal:8000/upload-resource';
        
        $payload = json_encode([
            'course_id'     => $course_id,
            'resource_id'   => $resource_id,
            'resource_type' => 'pdf',
            'file_url'      => 'http://host.docker.internal:8082/pluginfile.php/' . $course_id . '/mod_resource/content/0/'
        ]);

        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
        curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_exec($ch);
        curl_close($ch);
    }
}