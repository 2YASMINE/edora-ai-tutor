<?php
/**
 * Edora AI Tutor — Dashboard Administrateur
 * Vue globale : utilisateurs, cours, activité IA, monitoring API.
 *
 * @package block_tutor_ai
 */
require_once(__DIR__ . '/../../config.php');

require_login();
require_admin();

global $DB, $OUTPUT, $CFG;

$PAGE->set_url(new moodle_url('/blocks/tutor_ai/admin_dashboard.php'));
$PAGE->set_context(context_system::instance());
$PAGE->set_title('Edora — Administration IA');
$PAGE->set_heading('Edora AI Tutor — Administration');
$PAGE->set_pagelayout('embedded');

// ══════════════════════════════════════════════════════════════════════════════
// GARDE : vérifier l'existence des tables avant toute requête
// ══════════════════════════════════════════════════════════════════════════════
$has_usage_logs    = $DB->get_manager()->table_exists('edora_usage_logs');
$has_conversations = $DB->get_manager()->table_exists('edora_conversations');

// ── Données usage API (optionnel si table absente) ────────────────────────────
$global = (object)[
    'tokens_in'   => 0,
    'tokens_out'  => 0,
    'cost_usd'    => 0,
    'calls_count' => 0,
];
$bycourse_usage = [];

if ($has_usage_logs) {
    $global = $DB->get_record_sql("
        SELECT
            COALESCE(SUM(tokens_in),0)  AS tokens_in,
            COALESCE(SUM(tokens_out),0) AS tokens_out,
            COALESCE(SUM(cost_usd),0)   AS cost_usd,
            COUNT(*)                    AS calls_count
        FROM {edora_usage_logs}
    ");
    $bycourse_usage = $DB->get_records_sql("
        SELECT
            ul.course_id,
            c.fullname,
            COALESCE(SUM(ul.tokens_in),0)  AS tokens_in,
            COALESCE(SUM(ul.tokens_out),0) AS tokens_out,
            COALESCE(SUM(ul.cost_usd),0)   AS cost_usd,
            COUNT(*)                       AS calls_count
        FROM {edora_usage_logs} ul
        LEFT JOIN {course} c ON c.id = ul.course_id
        GROUP BY ul.course_id, c.fullname
        ORDER BY cost_usd DESC
        LIMIT 20
    ");
}

// ── Données conversations (stats pédagogiques) ────────────────────────────────
$total_conversations = 0;
$total_students      = 0;
$total_courses_active = 0;
$top_courses         = [];
$recent_activity     = [];
$task_distribution   = [];

if ($has_conversations) {
    $agg = $DB->get_record_sql("
        SELECT
            COUNT(*)                    AS total_conversations,
            COUNT(DISTINCT student_id)  AS total_students,
            COUNT(DISTINCT course_id)   AS total_courses_active
        FROM {edora_conversations}
    ");
    if ($agg) {
        $total_conversations  = (int)$agg->total_conversations;
        $total_students       = (int)$agg->total_students;
        $total_courses_active = (int)$agg->total_courses_active;
    }

    $top_courses = $DB->get_records_sql("
        SELECT
            ec.course_id,
            c.fullname,
            COUNT(*)                   AS nb_conversations,
            COUNT(DISTINCT student_id) AS nb_etudiants
        FROM {edora_conversations} ec
        LEFT JOIN {course} c ON c.id = ec.course_id
        GROUP BY ec.course_id, c.fullname
        ORDER BY nb_conversations DESC
        LIMIT 8
    ");

    $task_distribution = $DB->get_records_sql("
        SELECT task_type, COUNT(*) AS nb
        FROM {edora_conversations}
        WHERE task_type IS NOT NULL
        GROUP BY task_type
        ORDER BY nb DESC
        LIMIT 6
    ");

    $recent_activity = $DB->get_records_sql("
        SELECT
            DATE_FORMAT(created_at, '%d/%m') AS label,
            COUNT(*) AS nb
        FROM {edora_conversations}
        WHERE created_at >= DATE_SUB(NOW(), INTERVAL 14 DAY)
        GROUP BY DATE_FORMAT(created_at, '%Y-%m-%d'), DATE_FORMAT(created_at, '%d/%m')
        ORDER BY DATE_FORMAT(created_at, '%Y-%m-%d') ASC
    ");
}

// ── Infos plateforme Moodle ───────────────────────────────────────────────────
$total_users   = $DB->count_records('user',   ['deleted' => 0, 'confirmed' => 1]);
$total_courses = $DB->count_records('course',  ['visible' => 1]);

$admin_avatar = $OUTPUT->image_url('edo_admin_avatar', 'block_tutor_ai');

// ── Données JS pour le mini-graphe d'activité ─────────────────────────────────
$chart_labels = [];
$chart_values = [];
foreach ($recent_activity as $row) {
    $chart_labels[] = $row->label;
    $chart_values[] = (int)$row->nb;
}

$task_icons = [
    'expliquer'  => '📖',
    'quiz'       => '🧪',
    'exemple'    => '💡',
    'resumer'    => '📝',
    'flashcards' => '🃏',
    'distress'   => '🆘',
    'exam'       => '📋',
];
$task_labels_fr = [
    'expliquer'  => 'Expliquer',
    'quiz'       => 'Quiz',
    'exemple'    => 'Exemple',
    'resumer'    => 'Résumer',
    'flashcards' => 'Flashcards',
    'distress'   => 'Détresse',
    'exam'       => 'Examen',
];

echo $OUTPUT->header();
?>
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
/* ── Reset & tokens ─────────────────────────────────────────────────────── */
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}

:root{
    --teal-dark:#005f73;
    --teal:#0a9396;
    --teal-light:#94d2bd;
    --teal-pale:#e0f4f4;
    --amber:#f59e0b;
    --amber-pale:#fef3c7;
    --red:#ef4444;
    --red-pale:#fee2e2;
    --green:#10b981;
    --green-pale:#d1fae5;
    --blue:#3b82f6;
    --blue-pale:#dbeafe;
    --purple:#8b5cf6;
    --purple-pale:#ede9fe;

    --bg:#f0f4f8;
    --surface:#ffffff;
    --surface2:#f8fafc;
    --border:#e2e8f0;
    --border-teal:rgba(10,147,150,.18);
    --text:#1e293b;
    --text-muted:#64748b;
    --text-light:#94a3b8;

    --radius-sm:10px;
    --radius:16px;
    --radius-lg:20px;
    --shadow-sm:0 2px 8px rgba(0,0,0,.06);
    --shadow:0 4px 20px rgba(0,0,0,.08);
    --shadow-lg:0 8px 32px rgba(0,0,0,.12);
}

body{
    background:var(--bg);
    color:var(--text);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    font-size:14px;
    line-height:1.5;
    min-height:100vh;
}

/* ── Layout ─────────────────────────────────────────────────────────────── */
#edo-admin{display:flex;flex-direction:column;min-height:100vh}

/* ── Header — même style que student/teacher ────────────────────────────── */
.edo-header{
    background:linear-gradient(135deg,var(--teal-dark),var(--teal));
    padding:0 20px;
    height:68px;
    display:flex;
    align-items:center;
    gap:12px;
    color:#fff;
    flex-shrink:0;
    box-shadow:0 4px 16px rgba(0,95,115,.3);
    position:relative;
}
.edo-header::after{
    content:"";
    position:absolute;
    bottom:0;left:10%;right:10%;height:1px;
    background:linear-gradient(90deg,transparent,rgba(255,255,255,.3),transparent);
}
.edo-header-avatar{
    width:44px;height:44px;border-radius:50%;
    background:rgba(255,255,255,.12);
    border:2px solid rgba(255,255,255,.25);
    object-fit:contain;
    flex-shrink:0;
}
.edo-header-info{flex:1;min-width:0}
.edo-header-title{
    font-size:15px;font-weight:700;
    display:flex;align-items:center;gap:8px;
}
.edo-badge{
    font-size:9px;font-weight:700;letter-spacing:.06em;
    padding:2px 7px;border-radius:999px;
    background:rgba(255,255,255,.15);
    border:1px solid rgba(255,255,255,.25);
    color:#fff;
}
.edo-badge.admin{background:rgba(245,158,11,.25);border-color:rgba(245,158,11,.4)}
.edo-header-sub{font-size:11px;opacity:.75;margin-top:1px}

/* ── Alerte table absente ───────────────────────────────────────────────── */
.edo-alert{
    margin:16px 20px 0;padding:12px 16px;
    border-radius:var(--radius-sm);
    background:var(--amber-pale);
    border:1px solid rgba(245,158,11,.3);
    color:#92400e;font-size:13px;
    display:flex;align-items:center;gap:10px;
}
.edo-alert svg{flex-shrink:0}

/* ── Corps principal ────────────────────────────────────────────────────── */
.edo-body{padding:20px;display:flex;flex-direction:column;gap:18px;flex:1}

/* ── KPI grid — 2 rangées ───────────────────────────────────────────────── */
.edo-kpis{
    display:grid;
    grid-template-columns:repeat(4,1fr);
    gap:12px;
}
.edo-kpi{
    background:var(--surface);
    border:1px solid var(--border);
    border-radius:var(--radius);
    padding:18px 16px;
    box-shadow:var(--shadow-sm);
    display:flex;flex-direction:column;gap:6px;
    transition:box-shadow .2s;
    position:relative;
    overflow:hidden;
}
.edo-kpi::before{
    content:"";
    position:absolute;top:0;left:0;right:0;height:3px;
    background:var(--kpi-color,var(--teal));
    border-radius:var(--radius) var(--radius) 0 0;
}
.edo-kpi.amber{--kpi-color:var(--amber)}
.edo-kpi.green{--kpi-color:var(--green)}
.edo-kpi.blue{--kpi-color:var(--blue)}
.edo-kpi.purple{--kpi-color:var(--purple)}
.edo-kpi.red{--kpi-color:var(--red)}

.edo-kpi:hover{box-shadow:var(--shadow)}
.kpi-icon{font-size:22px;line-height:1}
.kpi-value{
    font-size:26px;font-weight:800;
    color:var(--kpi-color,var(--teal));
    line-height:1;
}
.kpi-label{font-size:11px;color:var(--text-muted);font-weight:500;text-transform:uppercase;letter-spacing:.04em}
.kpi-sub{font-size:11px;color:var(--text-light)}

/* ── Cards ──────────────────────────────────────────────────────────────── */
.edo-row{display:grid;gap:14px}
.edo-row.two{grid-template-columns:1fr 1fr}
.edo-row.three{grid-template-columns:2fr 1fr}

.edo-card{
    background:var(--surface);
    border:1px solid var(--border);
    border-radius:var(--radius);
    box-shadow:var(--shadow-sm);
    overflow:hidden;
}
.edo-card-head{
    padding:14px 18px;
    border-bottom:1px solid var(--border);
    display:flex;align-items:center;gap:10px;
    background:var(--surface2);
}
.edo-card-head h3{font-size:13px;font-weight:700;color:var(--text)}
.edo-card-head .ico{
    width:30px;height:30px;border-radius:8px;
    display:flex;align-items:center;justify-content:center;
    font-size:15px;
    background:var(--teal-pale);
}
.edo-card-body{padding:16px}

/* ── Table ──────────────────────────────────────────────────────────────── */
.edo-table{width:100%;border-collapse:collapse;font-size:12px}
.edo-table th{
    padding:8px 10px;
    color:var(--text-muted);
    font-size:10px;text-transform:uppercase;letter-spacing:.05em;
    border-bottom:2px solid var(--border);
    text-align:left;background:var(--surface2);
}
.edo-table td{
    padding:10px 10px;
    border-bottom:1px solid var(--border);
    color:var(--text);
}
.edo-table tr:last-child td{border-bottom:0}
.edo-table tr:hover td{background:var(--teal-pale)}
.cost-cell{color:var(--amber);font-weight:700}
.pill{
    display:inline-flex;align-items:center;gap:4px;
    padding:3px 8px;border-radius:999px;font-size:10px;font-weight:600;
}
.pill.teal{background:var(--teal-pale);color:var(--teal-dark)}
.pill.amber{background:var(--amber-pale);color:#92400e}
.pill.green{background:var(--green-pale);color:#065f46}
.pill.blue{background:var(--blue-pale);color:#1e40af}
.pill.purple{background:var(--purple-pale);color:#5b21b6}

/* ── Mini bar chart (JS-less) ────────────────────────────────────────────── */
.bar-row{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.bar-row:last-child{margin-bottom:0}
.bar-label{width:90px;font-size:11px;color:var(--text-muted);flex-shrink:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar-track{flex:1;height:8px;background:var(--border);border-radius:999px;overflow:hidden}
.bar-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,var(--teal),var(--teal-light));transition:width .6s ease}
.bar-num{width:36px;font-size:11px;font-weight:700;color:var(--text);text-align:right;flex-shrink:0}

/* ── Mini activity sparkline (Canvas) ───────────────────────────────────── */
#edo-sparkline{width:100%;height:80px;display:block}

/* ── Task icons grid ────────────────────────────────────────────────────── */
.task-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.task-item{
    display:flex;align-items:center;gap:10px;
    background:var(--surface2);border:1px solid var(--border);
    border-radius:var(--radius-sm);padding:10px 12px;
    transition:border-color .2s;
}
.task-item:hover{border-color:var(--teal)}
.task-item .t-ico{font-size:20px;line-height:1}
.task-item .t-info{flex:1;min-width:0}
.task-item .t-name{font-size:12px;font-weight:600;color:var(--text)}
.task-item .t-nb{font-size:10px;color:var(--text-muted)}

/* ── Empty state ────────────────────────────────────────────────────────── */
.edo-empty{
    padding:32px;text-align:center;color:var(--text-muted);font-size:13px;
}
.edo-empty .e-ico{font-size:36px;margin-bottom:10px}

/* ── Status indicator ───────────────────────────────────────────────────── */
.edo-status-dot{
    display:inline-block;width:8px;height:8px;border-radius:50%;
    background:var(--green);
    box-shadow:0 0 6px var(--green);
}
.edo-status-dot.warn{background:var(--amber);box-shadow:0 0 6px var(--amber)}

/* ── Section title ──────────────────────────────────────────────────────── */
.edo-section-title{
    font-size:11px;font-weight:700;color:var(--text-muted);
    text-transform:uppercase;letter-spacing:.07em;
    padding:0 2px;
}

/* ── Responsive ─────────────────────────────────────────────────────────── */
@media(max-width:900px){
    .edo-kpis{grid-template-columns:repeat(2,1fr)}
    .edo-row.two,.edo-row.three{grid-template-columns:1fr}
}
@media(max-width:560px){
    .edo-kpis{grid-template-columns:1fr 1fr}
    .edo-body{padding:14px}
    .kpi-value{font-size:22px}
    .task-grid{grid-template-columns:1fr}
}
</style>

<div id="edo-admin">

    <!-- ── HEADER ───────────────────────────────────────────────────────── -->
    <div class="edo-header">
        <img class="edo-header-avatar" src="<?= s($admin_avatar) ?>" alt="">
        <div class="edo-header-info">
            <div class="edo-header-title">
                Edora Administration
                <span class="edo-badge admin">ADMIN</span>
            </div>
            <div class="edo-header-sub">Monitoring global de la plateforme et de l'activité IA</div>
        </div>
        <span class="edo-status-dot <?= ($has_usage_logs && $has_conversations) ? '' : 'warn' ?>"
              title="<?= ($has_usage_logs && $has_conversations) ? 'Tables OK' : 'Tables manquantes' ?>"></span>
    </div>

    <div class="edo-body">

        <!-- ── ALERTE si tables absentes ────────────────────────────────── -->
        <?php if (!$has_usage_logs || !$has_conversations): ?>
        <div class="edo-alert">
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24"><path stroke="#92400e" stroke-width="2" stroke-linecap="round" d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/></svg>
            <span>
                <?php if (!$has_usage_logs && !$has_conversations): ?>
                    Tables <code>edora_usage_logs</code> et <code>edora_conversations</code> introuvables.
                <?php elseif (!$has_usage_logs): ?>
                    Table <code>edora_usage_logs</code> introuvable — les données de coûts API ne sont pas disponibles.
                <?php else: ?>
                    Table <code>edora_conversations</code> introuvable — les statistiques pédagogiques ne sont pas disponibles.
                <?php endif; ?>
                Lancez <code>db/install.php</code> ou réinstallez le plugin pour créer les tables manquantes.
            </span>
        </div>
        <?php endif; ?>

        <!-- ── KPIs PLATEFORME ───────────────────────────────────────────── -->
        <div class="edo-section-title">Vue globale plateforme</div>
        <div class="edo-kpis">

            <div class="edo-kpi blue">
                <div class="kpi-icon">👥</div>
                <div class="kpi-value"><?= number_format($total_users) ?></div>
                <div class="kpi-label">Utilisateurs actifs</div>
            </div>

            <div class="edo-kpi green">
                <div class="kpi-icon">📚</div>
                <div class="kpi-value"><?= number_format($total_courses) ?></div>
                <div class="kpi-label">Cours visibles</div>
                <div class="kpi-sub"><?= $total_courses_active ?> avec activité Edora</div>
            </div>

            <div class="edo-kpi" style="--kpi-color:var(--teal)">
                <div class="kpi-icon">🦉</div>
                <div class="kpi-value"><?= number_format($total_students) ?></div>
                <div class="kpi-label">Étudiants Edora</div>
                <div class="kpi-sub"><?= number_format($total_conversations) ?> conversations</div>
            </div>

            <div class="edo-kpi amber">
                <div class="kpi-icon">⚡</div>
                <div class="kpi-value"><?= number_format((int)$global->calls_count) ?></div>
                <div class="kpi-label">Appels API IA</div>
                <div class="kpi-sub">$<?= number_format((float)$global->cost_usd, 4) ?> total</div>
            </div>

        </div>

        <!-- ── KPIs TOKENS ──────────────────────────────────────────────── -->
        <div class="edo-section-title">Consommation API</div>
        <div class="edo-kpis">

            <div class="edo-kpi" style="--kpi-color:var(--teal)">
                <div class="kpi-icon">📥</div>
                <div class="kpi-value"><?= number_format((int)$global->tokens_in) ?></div>
                <div class="kpi-label">Tokens IN</div>
            </div>

            <div class="edo-kpi" style="--kpi-color:var(--teal)">
                <div class="kpi-icon">📤</div>
                <div class="kpi-value"><?= number_format((int)$global->tokens_out) ?></div>
                <div class="kpi-label">Tokens OUT</div>
            </div>

            <div class="edo-kpi amber">
                <div class="kpi-icon">💰</div>
                <div class="kpi-value">$<?= number_format((float)$global->cost_usd, 4) ?></div>
                <div class="kpi-label">Coût total USD</div>
            </div>

            <div class="edo-kpi" style="--kpi-color:var(--text-muted)">
                <div class="kpi-icon">📊</div>
                <div class="kpi-value"><?= $global->calls_count > 0 ? '$'.number_format((float)$global->cost_usd / (int)$global->calls_count, 6) : '—' ?></div>
                <div class="kpi-label">Coût / appel</div>
            </div>

        </div>

        <!-- ── ACTIVITÉ + TASKS ─────────────────────────────────────────── -->
        <div class="edo-row two">

            <!-- Mini sparkline activité 14j -->
            <div class="edo-card">
                <div class="edo-card-head">
                    <div class="ico">📈</div>
                    <h3>Activité Edora — 14 derniers jours</h3>
                </div>
                <div class="edo-card-body">
                    <?php if (!$has_conversations || empty($recent_activity)): ?>
                        <div class="edo-empty"><div class="e-ico">📭</div>Aucune activité enregistrée</div>
                    <?php else: ?>
                        <canvas id="edo-sparkline"></canvas>
                    <?php endif; ?>
                </div>
            </div>

            <!-- Distribution des tâches -->
            <div class="edo-card">
                <div class="edo-card-head">
                    <div class="ico">🎯</div>
                    <h3>Types d'interactions</h3>
                </div>
                <div class="edo-card-body">
                    <?php if (!$has_conversations || empty($task_distribution)): ?>
                        <div class="edo-empty"><div class="e-ico">📭</div>Aucune donnée</div>
                    <?php else: ?>
                        <?php
                        $task_max = max(array_map(fn($t) => (int)$t->nb, $task_distribution));
                        foreach ($task_distribution as $task):
                            $icon  = $task_icons[$task->task_type]  ?? '🔹';
                            $label = $task_labels_fr[$task->task_type] ?? ucfirst($task->task_type);
                            $pct   = $task_max > 0 ? round((int)$task->nb / $task_max * 100) : 0;
                        ?>
                        <div class="bar-row">
                            <div class="bar-label"><?= $icon ?> <?= s($label) ?></div>
                            <div class="bar-track"><div class="bar-fill" style="width:<?= $pct ?>%"></div></div>
                            <div class="bar-num"><?= number_format((int)$task->nb) ?></div>
                        </div>
                        <?php endforeach; ?>
                    <?php endif; ?>
                </div>
            </div>

        </div>

        <!-- ── TOP COURS (pédagogique) ──────────────────────────────────── -->
        <?php if ($has_conversations && !empty($top_courses)): ?>
        <div class="edo-card">
            <div class="edo-card-head">
                <div class="ico">🏆</div>
                <h3>Cours les plus actifs (Edora)</h3>
            </div>
            <div class="edo-card-body" style="padding:0">
                <table class="edo-table">
                    <thead>
                        <tr>
                            <th>Cours</th>
                            <th>Conversations</th>
                            <th>Étudiants</th>
                        </tr>
                    </thead>
                    <tbody>
                    <?php foreach ($top_courses as $row): ?>
                        <tr>
                            <td><?= s($row->fullname ?: ('Cours #'.$row->course_id)) ?></td>
                            <td><span class="pill teal"><?= number_format((int)$row->nb_conversations) ?></span></td>
                            <td><span class="pill blue"><?= number_format((int)$row->nb_etudiants) ?></span></td>
                        </tr>
                    <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        </div>
        <?php endif; ?>

        <!-- ── TOP COURS (usage API) ────────────────────────────────────── -->
        <?php if ($has_usage_logs && !empty($bycourse_usage)): ?>
        <div class="edo-card">
            <div class="edo-card-head">
                <div class="ico">💸</div>
                <h3>Consommation API par cours</h3>
            </div>
            <div class="edo-card-body" style="padding:0">
                <table class="edo-table">
                    <thead>
                        <tr>
                            <th>Cours</th>
                            <th>Appels</th>
                            <th>Tokens IN</th>
                            <th>Tokens OUT</th>
                            <th>Coût USD</th>
                        </tr>
                    </thead>
                    <tbody>
                    <?php foreach ($bycourse_usage as $row): ?>
                        <tr>
                            <td><?= s($row->fullname ?: ('Cours #'.$row->course_id)) ?></td>
                            <td><?= number_format((int)$row->calls_count) ?></td>
                            <td><?= number_format((int)$row->tokens_in) ?></td>
                            <td><?= number_format((int)$row->tokens_out) ?></td>
                            <td class="cost-cell">$<?= number_format((float)$row->cost_usd, 6) ?></td>
                        </tr>
                    <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        </div>
        <?php endif; ?>

        <!-- ── VIDE TOTAL ─────────────────────────────────────────────── -->
        <?php if (!$has_usage_logs && !$has_conversations): ?>
        <div class="edo-card">
            <div class="edo-card-body">
                <div class="edo-empty">
                    <div class="e-ico">🦉</div>
                    <div style="font-size:15px;font-weight:700;margin-bottom:6px">Edora est prêt</div>
                    <div>Les statistiques s'afficheront dès que des étudiants utiliseront l'assistant IA.</div>
                </div>
            </div>
        </div>
        <?php endif; ?>

    </div><!-- /edo-body -->
</div><!-- /edo-admin -->

<?php if (!empty($chart_labels)): ?>
<script>
(function(){
    var canvas = document.getElementById('edo-sparkline');
    if(!canvas) return;
    var ctx = canvas.getContext('2d');
    var labels = <?= json_encode($chart_labels) ?>;
    var values = <?= json_encode($chart_values) ?>;
    if(!values.length) return;

    // HiDPI
    var dpr = window.devicePixelRatio || 1;
    var W = canvas.offsetWidth || 340;
    var H = 80;
    canvas.width  = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width  = W + 'px';
    canvas.style.height = H + 'px';
    ctx.scale(dpr, dpr);

    var maxV = Math.max.apply(null, values) || 1;
    var pad  = {top:8, right:8, bottom:20, left:28};
    var cW   = W - pad.left - pad.right;
    var cH   = H - pad.top  - pad.bottom;
    var step = cW / Math.max(values.length - 1, 1);

    // Points
    var pts = values.map(function(v,i){
        return {
            x: pad.left + i * step,
            y: pad.top  + cH - (v / maxV) * cH
        };
    });

    // Gradient fill
    var grad = ctx.createLinearGradient(0, pad.top, 0, H - pad.bottom);
    grad.addColorStop(0, 'rgba(10,147,150,.25)');
    grad.addColorStop(1, 'rgba(10,147,150,.02)');

    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    pts.forEach(function(p,i){ if(i>0) ctx.lineTo(p.x, p.y); });
    ctx.lineTo(pts[pts.length-1].x, H - pad.bottom);
    ctx.lineTo(pts[0].x, H - pad.bottom);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // Line
    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    pts.forEach(function(p,i){ if(i>0) ctx.lineTo(p.x, p.y); });
    ctx.strokeStyle = '#0a9396';
    ctx.lineWidth   = 2;
    ctx.lineJoin    = 'round';
    ctx.stroke();

    // Dots
    pts.forEach(function(p){ 
        ctx.beginPath();
        ctx.arc(p.x, p.y, 3, 0, Math.PI*2);
        ctx.fillStyle = '#0a9396';
        ctx.fill();
    });

    // X labels (every 3rd)
    ctx.fillStyle = '#94a3b8';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'center';
    labels.forEach(function(l,i){
        if(i % 3 === 0) ctx.fillText(l, pts[i].x, H - 4);
    });

    // Y axis max label
    ctx.textAlign = 'right';
    ctx.fillText(maxV, pad.left - 4, pad.top + 4);
})();
</script>
<?php endif; ?>

<?php
echo $OUTPUT->footer();