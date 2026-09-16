<?php
defined('MOODLE_INTERNAL') || die();

class block_tutor_ai extends block_base {

    public function init() {
        $this->title = get_string('pluginname', 'block_tutor_ai');
    }

    public function get_content() {
        global $OUTPUT, $USER, $DB;

        if ($this->content !== null) {
            return $this->content;
        }

        $this->content         = new stdClass();
        $this->content->footer = '';

        $courseid = (int)$this->page->course->id;

        // ============================================================
        // FIX : s'assurer que le contexte de page est défini
        // ============================================================
        if (!$this->page->context) {
            if ($courseid > SITEID) {
                $this->page->set_context(context_course::instance($courseid));
            } else {
                $this->page->set_context(context_system::instance());
            }
        }

        // ============================================================
        // 1. ADMIN
        // ============================================================
        if (is_siteadmin()) {
            $url    = new moodle_url('/blocks/tutor_ai/admin_dashboard.php');
            $avatar = $OUTPUT->image_url('edo_admin_avatar', 'block_tutor_ai');

            $this->content->text = $this->build_dashboard_launcher(
                'admin',
                'Administration Edora',
                'Monitoring global, tokens, coûts et activité API.',
                $url,
                $avatar,
                'ADMIN'
            );
            return $this->content;
        }

        // ============================================================
        // 2. ENSEIGNANT
        // ============================================================
        // FIX 4 : detection independante du contexte de page / de l'inscription.
        // L'ancienne logique (enrol_get_users_courses) ne trouve rien sur les
        // pages hors-cours (ex: /my/) si l'utilisateur n'est pas "enrolled"
        // au sens strict (role attribue manuellement, etc.) -> le code tombait
        // alors par erreur dans la branche ETUDIANT. On verifie ici si le role
        // enseignant est attribue a l'utilisateur, dans N'IMPORTE QUEL contexte.
        $is_teacher    = false;
        $teacher_roles = ['editingteacher', 'teacher'];
        $roleids       = $DB->get_records_list('role', 'shortname', $teacher_roles, '', 'id, shortname');

        foreach ($roleids as $role) {
            if (user_has_role_assignment($USER->id, $role->id)) {
                $is_teacher = true;
                break;
            }
        }

        if ($is_teacher) {
            $params = [];
            if ($courseid > SITEID) {
                $params['course_id'] = $courseid;
            }

            $url    = new moodle_url('/blocks/tutor_ai/dashboard.php', $params);
            $avatar = $OUTPUT->image_url('edo_teacher_avatar', 'block_tutor_ai');

            $this->content->text = $this->build_dashboard_launcher(
                'teacher',
                'Edo Enseignant',
                'Suivi pédagogique de vos étudiants et de vos cours.',
                $url,
                $avatar,
                'ENSEIGNANT'
            );
            return $this->content;
        }

        // ============================================================
        // 3. ETUDIANT
        // ============================================================
        $url     = 'http://host.docker.internal:8000/health';
        $ch      = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 5);
        $response  = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($http_code !== 200) {
            $this->content->text = '<div class="edo-unavailable">
                <span class="edo-dot edo-dot--red"></span>
                Edo est indisponible pour le moment.
            </div>';
            return $this->content;
        }

        $student_id  = (int)$USER->id;
        $api_url     = 'http://localhost:8000';
        $course_lang = $this->page->course->lang ?: 'fr';
        $avatarurl   = $OUTPUT->image_url('edo_avatar', 'block_tutor_ai');

        $this->content->text = '<div id="edo-chat-root"
            data-course-id="' . $courseid . '"
            data-student-id="' . $student_id . '"
            data-api-url="'    . s($api_url) . '"
            data-avatar-url="' . s($avatarurl->out(false)) . '"
            data-lang="'       . s($course_lang) . '">
        </div>';

        $this->page->requires->css('/blocks/tutor_ai/styles.css');
        $this->page->requires->js('/blocks/tutor_ai/amd/src/chat.js');

        return $this->content;
    }

    private function build_dashboard_launcher(
        string      $role,
        string      $title,
        string      $subtitle,
        moodle_url  $url,
        \moodle_url $avatar,
        string      $badge
    ): string {

        $id         = 'edo-' . $role;
        // FIX 1 : appeler ->out(false) avant s() pour convertir l'objet moodle_url en chaîne
        $safeurl    = s($url->out(false));
        $safeavatar = s($avatar->out(false));
        $safetitle  = s($title);
        $safesub    = s($subtitle);
        $safebadge  = s($badge);

        $badge_style = ($role === 'admin')
            ? 'background:rgba(245,158,11,.22);border-color:rgba(245,158,11,.4);color:#fbbf24;'
            : 'background:rgba(255,255,255,.14);border-color:rgba(255,255,255,.22);color:#fff;';

        return '
<style>
/* FIX 3 : le bloc Moodle n\'affiche qu\'un placeholder vide — le FAB est injecté dans <body> */
#' . $id . '-block-placeholder { display: none; }

#' . $id . '-fab{
    position:fixed;right:24px;bottom:24px;
    width:58px;height:58px;border:0;border-radius:50%;cursor:pointer;padding:0;
    background:linear-gradient(135deg,#005f73,#0a9396);
    box-shadow:0 10px 28px rgba(0,95,115,.34);
    overflow:hidden;display:flex;align-items:center;justify-content:center;
    transition:transform .18s ease,box-shadow .18s ease;
    z-index:2147483646;
}
#' . $id . '-fab:hover{transform:translateY(-2px) scale(1.03);box-shadow:0 14px 34px rgba(0,95,115,.42)}
#' . $id . '-fab img{width:48px;height:48px;object-fit:contain;border-radius:50%}
</style>

<div id="' . $id . '-block-placeholder"></div>

<template id="' . $id . '-tpl">
<style>
#' . $id . '-panel{
    position:fixed;right:24px;bottom:24px;
    width:min(1180px,calc(100vw - 48px));
    height:min(780px,calc(100vh - 48px));
    z-index:2147483647;display:none;
    border-radius:20px;overflow:hidden;
    background:#f0f4f8;
    border:1px solid rgba(10,147,150,.2);
    box-shadow:0 24px 70px rgba(0,0,0,.28);
    flex-direction:column;
}
#' . $id . '-panel.open{
    display:flex;
    animation:edoPop_' . $role . ' .18s ease-out;
}
@keyframes edoPop_' . $role . '{
    from{opacity:0;transform:translateY(10px) scale(.985)}
    to{opacity:1;transform:none}
}
#' . $id . '-header{
    height:68px;flex:0 0 68px;
    padding:0 14px 0 16px;
    display:flex;align-items:center;gap:11px;
    color:#fff;
    background:linear-gradient(135deg,#005f73,#0a9396);
    flex-shrink:0;
}
#' . $id . '-header img{
    width:42px;height:42px;border-radius:50%;
    object-fit:contain;background:rgba(255,255,255,.12);
    border:2px solid rgba(255,255,255,.18);
}
#' . $id . '-info{min-width:0;flex:1}
#' . $id . '-htitle{font-size:14px;font-weight:700;display:flex;gap:8px;align-items:center}
#' . $id . '-hbadge{
    font-size:9px;padding:2px 7px;border-radius:999px;
    font-weight:700;letter-spacing:.04em;
    ' . $badge_style . '
}
#' . $id . '-hsub{font-size:11px;opacity:.76;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#' . $id . '-close,
#' . $id . '-newtab,
#' . $id . '-theme,
#' . $id . '-min{
    width:34px;height:34px;border-radius:10px;
    border:1px solid rgba(255,255,255,.18);
    background:rgba(255,255,255,.08);
    color:#fff;cursor:pointer;font-size:17px;
    display:flex;align-items:center;justify-content:center;
    transition:background .15s;flex-shrink:0;
}
#' . $id . '-close:hover,
#' . $id . '-newtab:hover,
#' . $id . '-theme:hover,
#' . $id . '-min:hover{background:rgba(255,255,255,.18)}
#' . $id . '-frame{border:0;width:100%;flex:1;min-height:0;background:#f0f4f8}

/* FIX 2 : minimisé → largeur fixe 460px, hauteur réduite à la barre de header */
#' . $id . '-panel.minimized{
    height:68px !important;
    min-height:68px;
    width:460px !important;
}
#' . $id . '-panel.minimized #' . $id . '-frame{display:none;}

@media(max-width:700px){
    #' . $id . '-panel{inset:8px;width:auto;height:auto;border-radius:16px}
    #' . $id . '-panel.minimized{inset:auto;right:8px;bottom:8px;width:calc(100vw - 16px) !important;}
}
</style>

<div id="' . $id . '-panel" aria-hidden="true" role="dialog" aria-label="' . $safetitle . '">
    <div id="' . $id . '-header">
        <img src="' . $safeavatar . '" alt="">
        <div id="' . $id . '-info">
            <div id="' . $id . '-htitle">
                ' . $safetitle . '
                <span id="' . $id . '-hbadge">' . $safebadge . '</span>
            </div>
            <div id="' . $id . '-hsub">' . $safesub . '</div>
        </div>
        <button id="' . $id . '-theme" type="button" title="Mode sombre / clair" aria-label="Basculer le theme"></button>
        <button id="' . $id . '-min" type="button" title="Reduire" aria-label="Reduire">&#8211;</button>
        <button id="' . $id . '-newtab" type="button" title="Nouvel onglet" aria-label="Nouvel onglet">&#8599;</button>
        <button id="' . $id . '-close" type="button" title="Fermer" aria-label="Fermer">&#215;</button>
    </div>
    <iframe id="' . $id . '-frame" src="about:blank" data-src="' . $safeurl . '" title="' . $safetitle . '" allowfullscreen></iframe>
</div>
</template>

<script>
(function(){
    var tpl = document.getElementById("' . $id . '-tpl");
    if (!tpl) return;

    var frag = tpl.content.cloneNode(true);
    document.body.appendChild(frag);

    // FIX 3 : créer et injecter le FAB dans <body> (position:fixed) plutôt que dans le bloc
    var fab = document.createElement("button");
    fab.id             = "' . $id . '-fab";
    fab.type           = "button";
    fab.setAttribute("aria-label", "Ouvrir ' . $safetitle . '");
    fab.innerHTML      = \'<img src="' . $safeavatar . '" alt="">\';
    document.body.appendChild(fab);

    var panel    = document.getElementById("' . $id . '-panel");
    var close    = document.getElementById("' . $id . '-close");
    var newtab   = document.getElementById("' . $id . '-newtab");
    var themeBtn = document.getElementById("' . $id . '-theme");
    var minBtn   = document.getElementById("' . $id . '-min");
    var frame    = document.getElementById("' . $id . '-frame");
    if (!panel || !frame) return;

    var THEME_KEY = "edora_theme";
    var SVG_MOON  = "<svg width=\'14\' height=\'14\' viewBox=\'0 0 24 24\' fill=\'none\' stroke=\'currentColor\' stroke-width=\'2\'><path d=\'M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z\'/></svg>";
    var SVG_SUN   = "<svg width=\'14\' height=\'14\' viewBox=\'0 0 24 24\' fill=\'none\' stroke=\'currentColor\' stroke-width=\'2\'><circle cx=\'12\' cy=\'12\' r=\'5\'/><line x1=\'12\' y1=\'1\' x2=\'12\' y2=\'3\'/><line x1=\'12\' y1=\'21\' x2=\'12\' y2=\'23\'/><line x1=\'1\' y1=\'12\' x2=\'3\' y2=\'12\'/><line x1=\'21\' y1=\'12\' x2=\'23\' y2=\'12\'/></svg>";

    function getTheme() {
        return localStorage.getItem(THEME_KEY) === "dark" ? "dark" : "light";
    }
    function applyThemeIcon() {
        themeBtn.innerHTML = getTheme() === "dark" ? SVG_SUN : SVG_MOON;
    }
    function frameUrlWithTheme(theme) {
        var base = frame.dataset.src;
        var sep  = base.indexOf("?") === -1 ? "?" : "&";
        return base + sep + "theme=" + theme;
    }
    function setTheme(theme) {
        localStorage.setItem(THEME_KEY, theme);
        applyThemeIcon();
        if (loaded) { frame.src = frameUrlWithTheme(theme); }
    }
    applyThemeIcon();

    var loaded = false;

    function openPanel() {
        if (!loaded) {
            frame.src = frameUrlWithTheme(getTheme());
            loaded = true;
        }
        panel.classList.remove("minimized");
        panel.classList.add("open");
        panel.setAttribute("aria-hidden", "false");
        fab.setAttribute("aria-expanded", "true");
        setTimeout(function(){ close.focus(); }, 200);
    }

    function closePanel() {
        panel.classList.remove("open");
        panel.classList.remove("minimized");
        panel.setAttribute("aria-hidden", "true");
        fab.setAttribute("aria-expanded", "false");
        fab.focus();
    }

    function toggleMinimize() {
        panel.classList.toggle("minimized");
        minBtn.textContent = panel.classList.contains("minimized") ? "\u25a2" : "\u2013";
        minBtn.title = panel.classList.contains("minimized") ? "Agrandir" : "Reduire";
    }

    fab.addEventListener("click", openPanel);
    close.addEventListener("click", closePanel);
    minBtn.addEventListener("click", toggleMinimize);
    themeBtn.addEventListener("click", function(){
        setTheme(getTheme() === "dark" ? "light" : "dark");
    });
    newtab.addEventListener("click", function(){
        window.open(frameUrlWithTheme(getTheme()), "_blank", "noopener,noreferrer");
    });
    document.addEventListener("keydown", function(e){
        if (e.key === "Escape" && panel.classList.contains("open")) { closePanel(); }
    });
    document.addEventListener("click", function(e){
        if (panel.classList.contains("open")
            && !panel.contains(e.target)
            && e.target !== fab
            && !fab.contains(e.target)) { closePanel(); }
    });
})();
</script>';
    }

    public function get_required_javascript() {
        return [];
    }

    public function applicable_formats() {
    return [
        'all' => true,
    ];
}
}