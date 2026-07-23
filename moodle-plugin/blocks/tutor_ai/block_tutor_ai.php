<?php
defined('MOODLE_INTERNAL') || die();

class block_tutor_ai extends block_base {

    public function init() {
        $this->title = get_string('pluginname', 'block_tutor_ai');
    }

    public function get_content() {
    if ($this->content !== null) {
        return $this->content;
    }

    // Appel HTTP vers le microservice FastAPI
    $url = 'http://host.docker.internal:8000/health';
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);

    $this->content = new stdClass();

    if ($http_code === 200) {
        $data = json_decode($response, true);
        $this->content->text = '<div id="tutor-ai-chat">
            <p>✅ Microservice IA connecté — version ' . $data['version'] . '</p>
        </div>';
    } else {
        $this->content->text = '<div id="tutor-ai-chat">
            <p>❌ Microservice IA indisponible</p>
        </div>';
    }

    $this->content->footer = '';
    return $this->content;
}

    // Déclenché automatiquement quand une ressource est ajoutée au cours
    public function instance_config_save($data, $nolongerused = false) {
        return parent::instance_config_save($data, $nolongerused);
    }
}

// Observer : déclenche /upload-resource quand un fichier est uploadé
function block_tutor_ai_after_file_created($file) {
    if ($file->get_component() !== 'mod_resource') {
        return;
    }

    $url = 'http://host.docker.internal:8000/upload-resource';
    $data = json_encode([
        'course_id'     => $file->get_contextid(),
        'resource_id'   => $file->get_itemid(),
        'resource_type' => 'pdf',
        'file_url'      => $file->get_filename()
    ]);

    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_POSTFIELDS, $data);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
    curl_exec($ch);
    curl_close($ch);
}