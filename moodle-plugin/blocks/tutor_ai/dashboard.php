<?php
/**
 * Edora AI Tutor — Dashboard Enseignant Analytique
 * Salle de contrôle pédagogique : heatmap, progression, alertes, coûts API
 *
 * @package    block_tutor_ai
 * @author     Islem Troudi
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

require_once(__DIR__ . '/../../config.php');
require_once($CFG->libdir . '/adminlib.php');

// ── Sécurité : dashboard strictement enseignant ──────────────────────────────
require_login();

// Un administrateur ne doit pas voir la vue enseignant.
if (is_siteadmin()) {
    redirect(new moodle_url('/blocks/tutor_ai/admin_dashboard.php'));
}

// Récupérer uniquement les cours dans lesquels l'utilisateur a réellement
// la capacité d'enseigner / gérer les activités.
$teacher_courses = [];
foreach (enrol_get_users_courses($USER->id, true) as $course) {
    $ctx = context_course::instance($course->id);
    if (has_capability('moodle/course:manageactivities', $ctx)) {
        $teacher_courses[$course->id] = $course;
    }
}

if (empty($teacher_courses)) {
    redirect(new moodle_url('/'), get_string('nopermissions', 'error'));
}

// ── Page setup ────────────────────────────────────────────────────────────────
$PAGE->set_url(new moodle_url('/blocks/tutor_ai/dashboard.php'));
$PAGE->set_context(context_system::instance());
$PAGE->set_title('Edora — Dashboard Enseignant');
$PAGE->set_heading('Edora AI Tutor — Tableau de bord enseignant');
$PAGE->set_pagelayout('embedded');

global $DB;

// ── Paramètre course_id + validation stricte ─────────────────────────────────
$selected_course = optional_param('course_id', 0, PARAM_INT);
$teacher_course_ids = array_map('intval', array_keys($teacher_courses));

if ($selected_course && !in_array($selected_course, $teacher_course_ids, true)) {
    throw new moodle_exception('nopermissions', 'error');
}

// ══════════════════════════════════════════════════════════════════════════════
// GARDE : vérifier l'existence de la table avant toute requête.
// Sans ce garde, un enseignant dont l'instance Moodle n'a pas encore la table
// edora_conversations (plugin fraîchement installé, migration non appliquée…)
// provoque une erreur SQL fatale (dml_read_exception) au lieu d'un dashboard vide.
// ══════════════════════════════════════════════════════════════════════════════
$has_conversations = $DB->get_manager()->table_exists('edora_conversations');

$courses_with_data   = [];
$stats               = null;
$heatmap_data        = [];
$level_progression   = [];
$alertes_bloques     = [];
$niveaux_distribution = [];
$activite_hebdo      = [];

if ($has_conversations) {
    // Ne proposer que les cours de cet enseignant qui possèdent des données Edora.
    list($insql, $inparams) = $DB->get_in_or_equal($teacher_course_ids, SQL_PARAMS_NAMED, 'tc');
    $courses_with_data = $DB->get_records_sql("
        SELECT DISTINCT ec.course_id, c.fullname
          FROM {edora_conversations} ec
          JOIN {course} c ON c.id = ec.course_id
         WHERE ec.course_id $insql
      ORDER BY c.fullname
    ", $inparams);
}

if ($selected_course === 0) {
    if (!empty($courses_with_data)) {
        $first = reset($courses_with_data);
        $selected_course = (int)$first->course_id;
    } else {
        $selected_course = (int)reset($teacher_course_ids);
    }
}

// ══════════════════════════════════════════════════════════════════════════════
// REQUÊTES SQL — données dashboard (uniquement si la table existe)
// ══════════════════════════════════════════════════════════════════════════════
if ($has_conversations) {

    // 1. Statistiques globales du cours
    $stats = $DB->get_record_sql("
        SELECT
            COUNT(DISTINCT ec.student_id)                          AS nb_etudiants,
            COUNT(*)                                               AS nb_conversations,
            COUNT(CASE WHEN ec.student_level = 'debutant'      THEN 1 END) AS nb_debutants,
            COUNT(CASE WHEN ec.student_level = 'intermediaire' THEN 1 END) AS nb_intermediaires,
            COUNT(CASE WHEN ec.student_level = 'avance'        THEN 1 END) AS nb_avances
        FROM {edora_conversations} ec
        WHERE ec.course_id = :course_id
    ", ['course_id' => $selected_course]);

    // 2. Heatmap des types de tâches (ce que les étudiants demandent le plus)
    $heatmap_data = $DB->get_records_sql("
        SELECT
            task_type,
            COUNT(*) AS nb_questions
        FROM {edora_conversations}
        WHERE course_id = :course_id
          AND task_type IS NOT NULL
          AND task_type NOT IN ('distress', 'exam')
        GROUP BY task_type
        ORDER BY nb_questions DESC
    ", ['course_id' => $selected_course]);

    // 3. Progression des niveaux dans le temps (par semaine)
    $level_progression = $DB->get_records_sql("
        SELECT
            DATE_FORMAT(created_at, '%Y-%u') AS semaine,
            DATE_FORMAT(MIN(created_at), '%d/%m')  AS label_date,
            COUNT(CASE WHEN student_level = 'debutant'      THEN 1 END) AS debutants,
            COUNT(CASE WHEN student_level = 'intermediaire' THEN 1 END) AS intermediaires,
            COUNT(CASE WHEN student_level = 'avance'        THEN 1 END) AS avances
        FROM {edora_conversations}
        WHERE course_id = :course_id
          AND student_level IS NOT NULL
        GROUP BY DATE_FORMAT(created_at, '%Y-%u')
        ORDER BY semaine ASC
        LIMIT 12
    ", ['course_id' => $selected_course]);

    // 4. Alertes : étudiants bloqués (3+ conversations sur le même cours sans progression)
    $alertes_bloques = $DB->get_records_sql("
        SELECT
            ec.student_id,
            COUNT(*) AS nb_conversations,
            MAX(ec.created_at) AS derniere_activite,
            ec.student_level
        FROM {edora_conversations} ec
        WHERE ec.course_id = :course_id
          AND ec.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        GROUP BY ec.student_id, ec.student_level
        HAVING COUNT(*) >= 3 AND (ec.student_level = 'debutant' OR ec.student_level IS NULL)
        ORDER BY nb_conversations DESC
        LIMIT 10
    ", ['course_id' => $selected_course]);

    // 5. Distribution des niveaux actuels
    $niveaux_distribution = $DB->get_records_sql("
        SELECT
            student_level,
            COUNT(DISTINCT student_id) AS nb_etudiants
        FROM {edora_conversations}
        WHERE course_id = :course_id
          AND student_level IS NOT NULL
        GROUP BY student_level
    ", ['course_id' => $selected_course]);

    // 6. Activité par jour de la semaine (heatmap temporelle)
    $activite_hebdo = $DB->get_records_sql("
        SELECT
            DAYOFWEEK(created_at) AS jour_num,
            DAYNAME(created_at)   AS jour_nom,
            COUNT(*)              AS nb_interactions
        FROM {edora_conversations}
        WHERE course_id = :course_id
        GROUP BY DAYOFWEEK(created_at), DAYNAME(created_at)
        ORDER BY DAYOFWEEK(created_at)
    ", ['course_id' => $selected_course]);
}

// ── Préparer données JSON pour Chart.js ───────────────────────────────────────

// Heatmap tâches
$heatmap_labels = [];
$heatmap_values = [];
$heatmap_icons  = ['chat' => '💬', 'quiz' => '🎯', 'resume' => '📋', 'expliquer' => '💡', 'exemple' => '🔍', 'flashcards' => '🃏'];
foreach ($heatmap_data as $row) {
    $icon = $heatmap_icons[$row->task_type] ?? '📌';
    $heatmap_labels[] = $icon . ' ' . ucfirst($row->task_type);
    $heatmap_values[] = (int)$row->nb_questions;
}

// Progression niveaux
$prog_labels = [];
$prog_debutants = [];
$prog_interm = [];
$prog_avances = [];
foreach ($level_progression as $row) {
    $prog_labels[]    = $row->label_date;
    $prog_debutants[] = (int)$row->debutants;
    $prog_interm[]    = (int)$row->intermediaires;
    $prog_avances[]   = (int)$row->avances;
}

// Distribution niveaux (doughnut)
$dist_labels = ['🌱 Débutant', '📘 Intermédiaire', '🚀 Avancé'];
$dist_values = [0, 0, 0];
foreach ($niveaux_distribution as $row) {
    if ($row->student_level === 'debutant')      $dist_values[0] = (int)$row->nb_etudiants;
    if ($row->student_level === 'intermediaire') $dist_values[1] = (int)$row->nb_etudiants;
    if ($row->student_level === 'avance')        $dist_values[2] = (int)$row->nb_etudiants;
}

// Activité hebdo
$jours_fr = [1=>'Dim', 2=>'Lun', 3=>'Mar', 4=>'Mer', 5=>'Jeu', 6=>'Ven', 7=>'Sam'];
$activite_labels = [];
$activite_values = [];
$activite_map = [];
foreach ($activite_hebdo as $row) { $activite_map[$row->jour_num] = (int)$row->nb_interactions; }
for ($j = 2; $j <= 7; $j++) {
    $activite_labels[] = $jours_fr[$j];
    $activite_values[] = $activite_map[$j] ?? 0;
}
$activite_labels[] = $jours_fr[1];
$activite_values[] = $activite_map[1] ?? 0;

$teacher_avatar = $OUTPUT->image_url('edo_teacher_avatar', 'block_tutor_ai');
echo $OUTPUT->header();
?>

<style>
/* ══════════════════════════════════════════════════
   EDORA DASHBOARD — Design system
   ══════════════════════════════════════════════════ */
:root {
    --edo-teal:   #005f73;
    --edo-cyan:   #22d3ee;
    --edo-dark:   #07090f;
    --edo-teal2:  #0a9396;
    --edo-teal-l: #e0f7fa;
    --edo-amber:  #f59e0b;
    --edo-red:    #ef4444;
    --edo-green:  #22c55e;
    --edo-purple: #7c3aed;
    --edo-bg:     #f8fafc;
    --edo-card:   #ffffff;
    --edo-border: #e2e8f0;
    --edo-text:   #1e293b;
    --edo-muted:  #64748b;
    --edo-radius: 14px;
    --edo-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 4px 16px rgba(0,0,0,0.04);
}

#edo-dashboard {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--edo-bg);
    min-height: 100%;
    padding: 0 0 28px;
    color: var(--edo-text);
}

/* ── Header ── */
.edo-dash-header {
    background: linear-gradient(135deg, var(--edo-teal) 0%, var(--edo-teal2) 100%);
    padding: 18px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 16px;
    margin-bottom: 28px;
}
.edo-dash-title {
    font-size: 22px;
    font-weight: 700;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 10px;
}
.edo-dash-subtitle {
    font-size: 13px;
    color: rgba(255,255,255,0.75);
    margin-top: 3px;
}
.edo-course-select {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}
.edo-course-select label {
    color: rgba(255,255,255,0.85);
    font-size: 13px;
    font-weight: 500;
}
.edo-course-select select {
    padding: 8px 14px;
    border-radius: 8px;
    border: 1px solid rgba(255,255,255,0.25);
    background: rgba(255,255,255,0.12);
    color: #fff;
    font-size: 13px;
    cursor: pointer;
    outline: none;
}
.edo-course-select select option { background: var(--edo-teal); color: #fff; }

/* ── Container ── */
.edo-dash-body { padding: 0 28px; }

/* ── KPI Cards ── */
.edo-kpi-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}
.edo-kpi {
    background: var(--edo-card);
    border: 1px solid var(--edo-border);
    border-radius: var(--edo-radius);
    padding: 20px 18px;
    box-shadow: var(--edo-shadow);
    display: flex;
    flex-direction: column;
    gap: 6px;
    transition: transform 0.15s, box-shadow 0.15s;
}
.edo-kpi:hover { transform: translateY(-2px); box-shadow: 0 4px 20px rgba(0,0,0,0.1); }
.edo-kpi-icon { font-size: 22px; }
.edo-kpi-value { font-size: 28px; font-weight: 700; color: var(--edo-teal); line-height: 1; }
.edo-kpi-label { font-size: 12px; color: var(--edo-muted); font-weight: 500; }
.edo-kpi-sub   { font-size: 11px; color: var(--edo-muted); }

/* ── Alertes ── */
.edo-alert-banner {
    background: #fff7ed;
    border: 1px solid #fed7aa;
    border-left: 4px solid var(--edo-amber);
    border-radius: var(--edo-radius);
    padding: 14px 18px;
    margin-bottom: 24px;
    display: flex;
    align-items: flex-start;
    gap: 12px;
}
.edo-alert-icon { font-size: 20px; flex-shrink: 0; margin-top: 1px; }
.edo-alert-title { font-size: 14px; font-weight: 600; color: #92400e; margin-bottom: 8px; }
.edo-alert-list  { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px; }
.edo-alert-item  { font-size: 13px; color: #78350f; display: flex; align-items: center; gap: 8px; }
.edo-alert-badge { background: #f97316; color: #fff; border-radius: 20px; padding: 2px 8px; font-size: 11px; font-weight: 600; }

/* ── Charts grid ── */
.edo-charts-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
    margin-bottom: 20px;
}
.edo-charts-grid.single { grid-template-columns: 1fr; }
.edo-charts-grid.three  { grid-template-columns: 2fr 1fr; }

.edo-card {
    background: var(--edo-card);
    border: 1px solid var(--edo-border);
    border-radius: var(--edo-radius);
    padding: 20px 22px;
    box-shadow: var(--edo-shadow);
}
.edo-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
}
.edo-card-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--edo-text);
    display: flex;
    align-items: center;
    gap: 7px;
}
.edo-card-badge {
    font-size: 11px;
    padding: 3px 9px;
    border-radius: 20px;
    background: var(--edo-teal-l);
    color: var(--edo-teal);
    font-weight: 500;
}
.edo-chart-wrap { position: relative; height: 220px; }
.edo-chart-wrap.tall { height: 260px; }

/* ── Table coûts ── */
.edo-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}
.edo-table th {
    text-align: left;
    padding: 8px 12px;
    background: var(--edo-bg);
    color: var(--edo-muted);
    font-weight: 500;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 1px solid var(--edo-border);
}
.edo-table td {
    padding: 10px 12px;
    border-bottom: 1px solid var(--edo-border);
    color: var(--edo-text);
}
.edo-table tr:last-child td { border-bottom: none; }
.edo-table tr:hover td { background: var(--edo-bg); }
.edo-cost-value { font-weight: 600; color: var(--edo-teal); }
.edo-pill {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 500;
}
.edo-pill-teal   { background: #e0f7fa; color: var(--edo-teal); }
.edo-pill-amber  { background: #fff7ed; color: #92400e; }
.edo-pill-purple { background: #f5f3ff; color: var(--edo-purple); }
.edo-pill-green  { background: #f0fdf4; color: #15803d; }
.edo-pill-gray   { background: #f1f5f9; color: var(--edo-muted); }

/* ── Vide ── */
.edo-empty {
    text-align: center;
    padding: 40px 20px;
    color: var(--edo-muted);
    font-size: 13px;
}
.edo-empty-icon { font-size: 32px; display: block; margin-bottom: 10px; }

/* ── Refresh badge ── */
.edo-refresh { font-size: 11px; color: var(--edo-muted); display: flex; align-items: center; gap: 5px; }

@media (max-width: 768px) {
    .edo-charts-grid, .edo-charts-grid.three { grid-template-columns: 1fr; }
    .edo-dash-header { padding: 20px 18px; }
    .edo-dash-body   { padding: 0 14px; }
}

/* ── Mode sombre ────────────────────────────────────────────────────────
   Toutes les couleurs de ce fichier reposent sur les custom properties
   --edo-*, donc les redéfinir sur <html data-theme="dark"> suffit à
   basculer l'intégralité du dashboard sans dupliquer les règles. ── */
html[data-theme="dark"] {
    --edo-bg:     #0b1220;
    --edo-card:   #111827;
    --edo-border: #1f2937;
    --edo-text:   #e2e8f0;
    --edo-muted:  #94a3b8;
    --edo-teal-l: rgba(10,147,150,.16);
}
html[data-theme="dark"] .edo-empty-icon,
html[data-theme="dark"] .edo-alert-icon { filter: brightness(1.15); }

/* ── Bouton bascule thème (ajouté dans le header) ─────────────────────── */
.edo-theme-toggle {
    width: 38px; height: 38px; border-radius: 10px;
    border: 1px solid rgba(255,255,255,.25);
    background: rgba(255,255,255,.12);
    color: #fff; cursor: pointer; font-size: 16px;
    display: flex; align-items: center; justify-content: center;
    transition: background .15s;
}
.edo-theme-toggle:hover { background: rgba(255,255,255,.22); }

/* ── Bandeau "table absente" (cohérent avec admin_dashboard.php) ────────── */
.edo-table-missing {
    margin: 16px 24px 0;
    padding: 12px 16px;
    border-radius: 10px;
    background: #fef3c7;
    border: 1px solid rgba(245,158,11,.3);
    color: #92400e;
    font-size: 13px;
    display: flex; align-items: center; gap: 10px;
}
html[data-theme="dark"] .edo-table-missing {
    background: rgba(245,158,11,.14);
    border-color: rgba(245,158,11,.35);
    color: #fbbf24;
}
</style>

<script>
// Applique le thème AVANT le rendu du corps pour éviter le flash clair/sombre.
// Priorité : paramètre ?theme= (passé par le popup parent) > préférence locale.
(function () {
    var params = new URLSearchParams(window.location.search);
    var fromUrl = params.get('theme');
    var theme = (fromUrl === 'dark' || fromUrl === 'light')
        ? fromUrl
        : (localStorage.getItem('edora_theme') === 'dark' ? 'dark' : 'light');
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('edora_theme', theme);
})();
</script>

<div id="edo-dashboard">

<?php if (!$has_conversations): ?>
<div class="edo-table-missing">
    ⚠️ Table <code>edora_conversations</code> introuvable — les statistiques pédagogiques ne sont pas disponibles.
    Réinstallez le plugin ou lancez <code>db/install.php</code> pour créer la table manquante.
</div>
<?php endif; ?>

<!-- ══ HEADER ══════════════════════════════════════════════════════════════ -->
<div class="edo-dash-header">
    <div>
        <div class="edo-dash-title">
            <img src="<?= $teacher_avatar ?>" alt="" style="width:42px;height:42px;border-radius:50%;object-fit:contain;background:rgba(255,255,255,.12);padding:3px;">
            Tableau de bord Enseignant
        </div>
        <div class="edo-dash-subtitle">Edora AI Tutor — Salle de contrôle pédagogique</div>
    </div>
    <div class="edo-course-select">
        <label>📚 Cours :</label>
        <form method="get" style="display:inline;">
            <select name="course_id" onchange="this.form.submit()">
                <?php foreach ($courses_with_data as $c): ?>
                    <option value="<?= $c->course_id ?>"
                        <?= $c->course_id == $selected_course ? 'selected' : '' ?>>
                        <?= htmlspecialchars($c->fullname ?: 'Cours ' . $c->course_id) ?>
                    </option>
                <?php endforeach; ?>
            </select>
        </form>
        <div class="edo-refresh">
            🕐 <?= date('H:i') ?>
            <a href="?course_id=<?= $selected_course ?>" style="color:var(--edo-teal2);text-decoration:none;">↻ Rafraîchir</a>
        </div>
    </div>
</div>

<div class="edo-dash-body">

<!-- ══ KPI ROW ═════════════════════════════════════════════════════════════ -->
<div class="edo-kpi-row">
    <div class="edo-kpi">
        <div class="edo-kpi-icon">👥</div>
        <div class="edo-kpi-value"><?= $stats ? (int)$stats->nb_etudiants : 0 ?></div>
        <div class="edo-kpi-label">Étudiants actifs</div>
        <div class="edo-kpi-sub">ayant utilisé Edora</div>
    </div>
    <div class="edo-kpi">
        <div class="edo-kpi-icon">💬</div>
        <div class="edo-kpi-value"><?= $stats ? (int)$stats->nb_conversations : 0 ?></div>
        <div class="edo-kpi-label">Interactions totales</div>
        <div class="edo-kpi-sub">questions posées au tuteur</div>
    </div>
    <div class="edo-kpi">
        <div class="edo-kpi-icon">🌱</div>
        <div class="edo-kpi-value"><?= $stats ? (int)$stats->nb_debutants : 0 ?></div>
        <div class="edo-kpi-label">Débutants</div>
        <div class="edo-kpi-sub">niveau détecté par quiz</div>
    </div>
    <div class="edo-kpi">
        <div class="edo-kpi-icon">📘</div>
        <div class="edo-kpi-value"><?= $stats ? (int)$stats->nb_intermediaires : 0 ?></div>
        <div class="edo-kpi-label">Intermédiaires</div>
        <div class="edo-kpi-sub">niveau détecté par quiz</div>
    </div>
    <div class="edo-kpi">
        <div class="edo-kpi-icon">🚀</div>
        <div class="edo-kpi-value"><?= $stats ? (int)$stats->nb_avances : 0 ?></div>
        <div class="edo-kpi-label">Avancés</div>
        <div class="edo-kpi-sub">niveau détecté par quiz</div>
    </div>
</div>

<!-- ══ ALERTES ÉTUDIANTS BLOQUÉS ═══════════════════════════════════════════ -->
<?php if (!empty($alertes_bloques)): ?>
<div class="edo-alert-banner">
    <div class="edo-alert-icon">⚠️</div>
    <div style="flex:1;">
        <div class="edo-alert-title">Étudiants potentiellement bloqués — 7 derniers jours</div>
        <ul class="edo-alert-list">
            <?php foreach ($alertes_bloques as $a): ?>
            <li class="edo-alert-item">
                <span class="edo-alert-badge"><?= (int)$a->nb_conversations ?>x</span>
                Étudiant #<?= substr(hash('sha256', (string)$a->student_id), 0, 8) ?>
                — Niveau : <strong><?= $a->student_level ?: 'Non évalué' ?></strong>
                — Dernière activité : <?= date('d/m H:i', strtotime($a->derniere_activite)) ?>
            </li>
            <?php endforeach; ?>
        </ul>
    </div>
</div>
<?php endif; ?>

<!-- ══ LIGNE 1 : Heatmap + Progression ════════════════════════════════════ -->
<div class="edo-charts-grid">

    <!-- Heatmap types de questions -->
    <div class="edo-card">
        <div class="edo-card-header">
            <div class="edo-card-title">🔥 Ce que les étudiants demandent le plus</div>
            <span class="edo-card-badge">Heatmap</span>
        </div>
        <?php if (empty($heatmap_data)): ?>
            <div class="edo-empty"><span class="edo-empty-icon">📊</span>Pas encore de données pour ce cours</div>
        <?php else: ?>
            <div class="edo-chart-wrap">
                <canvas id="chartHeatmap"></canvas>
            </div>
        <?php endif; ?>
    </div>

    <!-- Distribution des niveaux -->
    <div class="edo-card">
        <div class="edo-card-header">
            <div class="edo-card-title">🎓 Distribution des niveaux</div>
            <span class="edo-card-badge">Doughnut</span>
        </div>
        <?php if (array_sum($dist_values) === 0): ?>
            <div class="edo-empty"><span class="edo-empty-icon">🎓</span>Aucun niveau détecté pour ce cours</div>
        <?php else: ?>
            <div class="edo-chart-wrap">
                <canvas id="chartDist"></canvas>
            </div>
        <?php endif; ?>
    </div>

</div>

<!-- ══ LIGNE 2 : Progression temporelle + Activité hebdo ══════════════════ -->
<div class="edo-charts-grid three">

    <!-- Progression niveaux dans le temps -->
    <div class="edo-card">
        <div class="edo-card-header">
            <div class="edo-card-title">📈 Progression des niveaux dans le temps</div>
            <span class="edo-card-badge">Semaines</span>
        </div>
        <?php if (empty($level_progression)): ?>
            <div class="edo-empty"><span class="edo-empty-icon">📈</span>Données insuffisantes (quiz non encore effectués)</div>
        <?php else: ?>
            <div class="edo-chart-wrap tall">
                <canvas id="chartProgression"></canvas>
            </div>
        <?php endif; ?>
    </div>

    <!-- Activité par jour de semaine -->
    <div class="edo-card">
        <div class="edo-card-header">
            <div class="edo-card-title">📅 Activité par jour</div>
            <span class="edo-card-badge">Cette semaine</span>
        </div>
        <div class="edo-chart-wrap tall">
            <canvas id="chartActivite"></canvas>
        </div>
    </div>

</div>

</div><!-- .edo-dash-body -->
</div><!-- #edo-dashboard -->

<!-- ══ CHART.JS ═══════════════════════════════════════════════════════════ -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
// ── Données PHP → JS ──────────────────────────────────────────────────────
const heatmapLabels = <?= json_encode(array_values($heatmap_labels)) ?>;
const heatmapValues = <?= json_encode(array_values($heatmap_values)) ?>;

const progLabels    = <?= json_encode(array_values($prog_labels)) ?>;
const progDebutants = <?= json_encode(array_values($prog_debutants)) ?>;
const progInterm    = <?= json_encode(array_values($prog_interm)) ?>;
const progAvances   = <?= json_encode(array_values($prog_avances)) ?>;

const distLabels    = <?= json_encode($dist_labels) ?>;
const distValues    = <?= json_encode($dist_values) ?>;

const activiteLabels = <?= json_encode(array_values($activite_labels)) ?>;
const activiteValues = <?= json_encode(array_values($activite_values)) ?>;


Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
Chart.defaults.font.size   = 12;
Chart.defaults.color       = '#64748b';

// ── 1. Heatmap types de questions (Bar horizontal) ────────────────────────
const ctxHeatmap = document.getElementById('chartHeatmap');
if (ctxHeatmap && heatmapLabels.length > 0) {
    const maxVal = Math.max(...heatmapValues);
    const bgColors = heatmapValues.map(v => {
        const intensity = v / maxVal;
        const r = Math.round(10  + intensity * (0   - 10));
        const g = Math.round(147 + intensity * (95  - 147));
        const b = Math.round(150 + intensity * (115 - 150));
        return `rgba(${r}, ${g}, ${b}, ${0.4 + intensity * 0.6})`;
    });
    new Chart(ctxHeatmap, {
        type: 'bar',
        data: {
            labels: heatmapLabels,
            datasets: [{
                label: 'Nombre de questions',
                data: heatmapValues,
                backgroundColor: bgColors,
                borderColor: bgColors.map(c => c.replace(/[\d.]+\)$/, '1)')),
                borderWidth: 1,
                borderRadius: 6,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { stepSize: 1 } },
                y: { grid: { display: false } }
            }
        }
    });
}

// ── 2. Distribution niveaux (Doughnut) ────────────────────────────────────
const ctxDist = document.getElementById('chartDist');
if (ctxDist && distValues.some(v => v > 0)) {
    new Chart(ctxDist, {
        type: 'doughnut',
        data: {
            labels: distLabels,
            datasets: [{
                data: distValues,
                backgroundColor: ['#86efac', '#67e8f9', '#a78bfa'],
                borderColor:     ['#22c55e', '#22d3ee', '#7c3aed'],
                borderWidth: 2,
                hoverOffset: 8,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { padding: 16, usePointStyle: true } }
            },
            cutout: '65%'
        }
    });
}

// ── 3. Progression niveaux dans le temps (Line) ───────────────────────────
const ctxProg = document.getElementById('chartProgression');
if (ctxProg && progLabels.length > 0) {
    new Chart(ctxProg, {
        type: 'line',
        data: {
            labels: progLabels,
            datasets: [
                {
                    label: '🌱 Débutants',
                    data: progDebutants,
                    borderColor: '#22c55e',
                    backgroundColor: 'rgba(34,197,94,0.1)',
                    tension: 0.4, fill: true, pointRadius: 4, pointHoverRadius: 6,
                },
                {
                    label: '📘 Intermédiaires',
                    data: progInterm,
                    borderColor: '#22d3ee',
                    backgroundColor: 'rgba(34,211,238,0.1)',
                    tension: 0.4, fill: true, pointRadius: 4, pointHoverRadius: 6,
                },
                {
                    label: '🚀 Avancés',
                    data: progAvances,
                    borderColor: '#7c3aed',
                    backgroundColor: 'rgba(124,58,237,0.1)',
                    tension: 0.4, fill: true, pointRadius: 4, pointHoverRadius: 6,
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, padding: 14 } } },
            scales: {
                x: { grid: { color: '#f1f5f9' } },
                y: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { stepSize: 1 } }
            }
        }
    });
}

// ── 4. Activité par jour (Bar) ────────────────────────────────────────────
const ctxActivite = document.getElementById('chartActivite');
if (ctxActivite) {
    new Chart(ctxActivite, {
        type: 'bar',
        data: {
            labels: activiteLabels,
            datasets: [{
                label: 'Interactions',
                data: activiteValues,
                backgroundColor: activiteValues.map(v => v === Math.max(...activiteValues)
                    ? 'rgba(0,95,115,0.85)' : 'rgba(10,147,150,0.4)'),
                borderColor: 'rgba(0,95,115,0.9)',
                borderWidth: 1,
                borderRadius: 6,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false } },
                y: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { stepSize: 1 } }
            }
        }
    });
}

</script>

<?php
echo $OUTPUT->footer();