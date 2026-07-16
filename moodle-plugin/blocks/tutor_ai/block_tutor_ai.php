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
}