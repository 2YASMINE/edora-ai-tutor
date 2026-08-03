<?php
defined('MOODLE_INTERNAL') || die();

class block_tutor_ai extends block_base {

    public function init() {
        $this->title = get_string('pluginname', 'block_tutor_ai');
    }

    public function get_content() {
        global $OUTPUT;  // ← déclarer $OUTPUT comme variable globale

        if ($this->content !== null) {
            return $this->content;
        }

        $url = 'http://host.docker.internal:8000/health';
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 5);
        $response = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        $this->content = new stdClass();

        if ($http_code !== 200) {
            $this->content->text = '<div class="edo-unavailable">
                <span class="edo-dot edo-dot--red"></span>
                Edo est indisponible pour le moment.
            </div>';
            $this->content->footer = '';
            return $this->content;
        }

        $course_id = $this->page->course->id;
        $api_url   = "http://localhost:8000";

        // URL de l'avatar hibou via Moodle
        $avatarurl = $OUTPUT->image_url('edo-avatar', 'block_tutor_ai');

        $this->content->text = '<div id="edo-chat-root"
            data-course-id="' . (int)$course_id . '"
            data-api-url="' . $api_url . '"
            data-avatar-url="' . $avatarurl . '">
        </div>';

        $this->page->requires->css('/blocks/tutor_ai/styles.css');
        $this->page->requires->js('/blocks/tutor_ai/amd/src/chat.js');

        $this->content->footer = '';
        return $this->content;
    }

    public function get_required_javascript() {
        return [];
    }
}