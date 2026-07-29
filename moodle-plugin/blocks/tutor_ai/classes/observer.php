<?php
defined('MOODLE_INTERNAL') || die();

class block_tutor_ai_observer {

    public static function course_module_created(\core\event\course_module_created $event) {

        $data = $event->get_data();

        if ($data['other']['modulename'] !== 'resource') {
            return;
        }

        $courseid   = $data['courseid'];
        $resourceid = $data['objectid'];

        $cm = get_coursemodule_from_id('resource', $resourceid);
        if (!$cm) {
            return;
        }

        $context = context_module::instance($cm->id);

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

        $allowed       = ['pdf', 'docx', 'pptx', 'txt'];
        $resource_type = in_array($extension, $allowed) ? $extension : 'pdf';

        $token = '415bb98e8067544c4146182248d69dfe';

        $file_url = 'http://host.docker.internal:8082/tokenpluginfile.php/'
            . $token . '/'
            . $file->get_contextid()
            . '/mod_resource/content/0/'
            . rawurlencode($filename);

        $payload = json_encode([
            'course_id'     => (int) $courseid,
            'resource_id'   => (int) $resourceid,
            'resource_type' => $resource_type,
            'file_url'      => $file_url
        ]);

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