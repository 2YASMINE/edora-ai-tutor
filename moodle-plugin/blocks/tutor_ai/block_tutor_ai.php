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

        // Vérifier que le microservice est disponible
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

        // Récupérer le course_id courant
        $course_id = $this->page->course->id;

        // Injecter les variables PHP → JS via data attributes (pas de JS inline)
        $this->content->text = '
        <div id="edo-chat-root"
             data-course-id="' . (int)$course_id . '"
             data-api-url="http://host.docker.internal:8000">

            <!-- En-tête -->
            <div class="edo-header">
                <span class="edo-dot edo-dot--green"></span>
                <span class="edo-name">Edo</span>
                <span class="edo-subtitle">Tuteur IA</span>
            </div>

            <!-- Fenêtre messages -->
            <div id="edo-messages" class="edo-messages" role="log" aria-live="polite">
                <div class="edo-bubble edo-bubble--bot">
                    Bonjour ! Je suis Edo, ton tuteur. Pose-moi une question sur le cours 🎓
                </div>
            </div>

            <!-- Zone de saisie -->
            <div class="edo-input-row">
                <input
                    type="text"
                    id="edo-input"
                    class="edo-input"
                    placeholder="Pose ta question…"
                    aria-label="Question pour Edo"
                    maxlength="500"
                />
                <button id="edo-send" class="edo-send-btn" aria-label="Envoyer">
                    ➤
                </button>
            </div>
        </div>';

        // Charger le module AMD (Moodle gère le cache-busting automatiquement)
        $this->page->requires->js('/blocks/tutor_ai/amd/src/chat.js');
        $this->content->footer = '';
        return $this->content;
    }
}