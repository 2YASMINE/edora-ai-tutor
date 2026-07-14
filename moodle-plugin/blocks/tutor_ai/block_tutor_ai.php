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
        $this->content = new stdClass();
        $this->content->text = '<div id="tutor-ai-chat"><p>Tutor AI - Coming Soon</p></div>';
        $this->content->footer = '';
        return $this->content;
    }
}