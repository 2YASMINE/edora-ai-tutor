<?php
/**
 * Edora AI Tutor — Dashboard Administrateur
 * Vue globale : utilisateurs, cours, activité IA, monitoring API.
 *
 * IMPORTANT : Ce fichier génère son propre HTML autonome (pas de $OUTPUT->header).
 * Raison : chargé dans une iframe par block_tutor_ai.php — $OUTPUT->header() en
 * mode embedded injecte des headers X-Frame-Options / CSP qui bloquent l'iframe.
 *
 * @package block_tutor_ai
 */
require_once(__DIR__ . '/../../config.php');

// Sécurité : réservé aux admins
require_login();
require_admin();

// FIX : définir le contexte de page AVANT tout appel à $OUTPUT
$PAGE->set_context(context_system::instance());
$PAGE->set_url(new moodle_url('/blocks/tutor_ai/admin_dashboard.php'));

global $DB, $OUTPUT, $CFG;

// ── Thème passé par le launcher via ?theme=dark|light ────────────────────────
$theme = optional_param('theme', 'light', PARAM_ALPHA);
if (!in_array($theme, ['dark', 'light'])) {
    $theme = 'light';
}

// ══════════════════════════════════════════════════════════════════════════════
// GARDE : vérifier l'existence des tables avant toute requête
// ══════════════════════════════════════════════════════════════════════════════
$has_usage_logs    = $DB->get_manager()->table_exists('edora_usage_logs');
$has_conversations = $DB->get_manager()->table_exists('edora_conversations');

// ── Données usage API ─────────────────────────────────────────────────────────
$global = (object)[
    'tokens_in'   => 0,
    'tokens_out'  => 0,
    'cost_usd'    => 0.0,
    'calls_count' => 0,
];
$bycourse_usage = [];

if ($has_usage_logs) {
    $row = $DB->get_record_sql("
        SELECT
            COALESCE(SUM(tokens_in),0)  AS tokens_in,
            COALESCE(SUM(tokens_out),0) AS tokens_out,
            COALESCE(SUM(cost_usd),0)   AS cost_usd,
            COUNT(*)                    AS calls_count
        FROM {edora_usage_logs}
    ");
    if ($row) { $global = $row; }

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

// ── Données conversations ─────────────────────────────────────────────────────
$total_conversations  = 0;
$total_students       = 0;
$total_courses_active = 0;
$top_courses          = [];
$recent_activity      = [];
$task_distribution    = [];

if ($has_conversations) {
    $agg = $DB->get_record_sql("
        SELECT
            COUNT(*)                   AS total_conversations,
            COUNT(DISTINCT user_id)    AS total_students,
            COUNT(DISTINCT course_id)  AS total_courses_active
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
            COUNT(*)                 AS nb_conversations,
            COUNT(DISTINCT user_id)  AS nb_etudiants
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
$total_users   = $DB->count_records('user',  ['deleted' => 0, 'confirmed' => 1]);
$total_courses = $DB->count_records('course', ['visible' => 1]);

// FIX : out(false) → string propre
$admin_avatar = $OUTPUT->image_url('edo_admin_avatar', 'block_tutor_ai')->out(false);

// ── Données pour graphes ──────────────────────────────────────────────────────
$chart_labels = [];
$chart_values = [];
foreach ($recent_activity as $row) {
    $chart_labels[] = $row->label;
    $chart_values[] = (int)$row->nb;
}

$task_icons = [
    'expliquer'  => '📖', 'quiz' => '🧪', 'exemple' => '💡',
    'resumer'    => '📝', 'flashcards' => '🃏',
    'distress'   => '🆘', 'exam' => '📋',
];
$task_labels_fr = [
    'expliquer'  => 'Expliquer', 'quiz' => 'Quiz', 'exemple' => 'Exemple',
    'resumer'    => 'Résumer',   'flashcards' => 'Flashcards',
    'distress'   => 'Détresse',  'exam' => 'Examen',
];

// ══════════════════════════════════════════════════════════════════════════════
// HTML AUTONOME — pas de $OUTPUT->header() pour éviter les restrictions iframe
// ══════════════════════════════════════════════════════════════════════════════
header('Content-Type: text/html; charset=utf-8');
?>
<!DOCTYPE html>
<html lang="fr" data-theme="<?= s($theme) ?>">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Edora — Administration IA</title>
<style>
/* ── Tokens light ──────────────────────────────────────────────────────────── */
:root {
    --teal-dark : #005f73;
    --teal      : #0a9396;
    --teal-light: #94d2bd;
    --teal-pale : #e0f4f4;
    --amber     : #f59e0b;
    --amber-pale: #fef3c7;
    --red       : #ef4444;
    --red-pale  : #fee2e2;
    --green     : #10b981;
    --green-pale: #d1fae5;
    --blue      : #3b82f6;
    --blue-pale : #dbeafe;
    --purple    : #8b5cf6;
    --purple-pale:#ede9fe;

    --bg        : #f0f4f8;
    --surface   : #ffffff;
    --surface2  : #f8fafc;
    --border    : #e2e8f0;

    --text      : #1e293b;
    --text-muted: #64748b;
    --text-light: #94a3b8;

    --radius-sm : 10px;
    --radius    : 16px;
    --shadow-sm : 0 2px 8px rgba(0,0,0,.06);
    --shadow    : 0 4px 20px rgba(0,0,0,.08);

    --spark-stroke: #0a9396;
    --spark-f0    : rgba(10,147,150,.25);
    --spark-f1    : rgba(10,147,150,.02);
    --spark-label : #94a3b8;
}

/* ── Tokens dark ───────────────────────────────────────────────────────────── */
[data-theme="dark"] {
    --bg        : #0f1923;
    --surface   : #162230;
    --surface2  : #1a2a38;
    --border    : rgba(255,255,255,.08);

    --text      : #e2e8f0;
    --text-muted: #94a3b8;
    --text-light: #64748b;

    --teal-pale : #0a2a30;
    --amber-pale: #2a1f00;
    --red-pale  : #2a0a0a;
    --green-pale: #0a2a1a;
    --blue-pale : #0a1a2a;
    --purple-pale:#1a0a2a;

    --shadow-sm : 0 2px 8px rgba(0,0,0,.3);
    --shadow    : 0 4px 20px rgba(0,0,0,.4);

    --spark-stroke: #0a9396;
    --spark-f0    : rgba(10,147,150,.35);
    --spark-f1    : rgba(10,147,150,.04);
    --spark-label : #475569;
}

/* ── Reset ─────────────────────────────────────────────────────────────────── */
*,*::before,*::after { box-sizing:border-box; margin:0; padding:0 }

html, body {
    height:100%;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 14px;
    line-height: 1.5;
    transition: background .25s, color .25s;
}

/* ── Layout ────────────────────────────────────────────────────────────────── */
#edo-admin { display:flex; flex-direction:column; min-height:100vh }

/* ── Status dot (toujours utilisé dans edo-body si besoin futur) ─────────── */
.edo-status {
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    background: var(--green); box-shadow: 0 0 6px var(--green);
}
.edo-status.warn { background: var(--amber); box-shadow: 0 0 6px var(--amber) }

/* ── Alerte ────────────────────────────────────────────────────────────────── */
.edo-alert {
    margin: 14px 16px 0; padding: 12px 14px;
    border-radius: var(--radius-sm);
    background: var(--amber-pale);
    border: 1px solid rgba(245,158,11,.3);
    color: #92400e;
    font-size: 13px;
    display: flex; align-items: flex-start; gap: 10px;
}
[data-theme="dark"] .edo-alert { color: #fcd34d }
.edo-alert code {
    font-family: monospace; font-size: 12px;
    background: rgba(0,0,0,.08); border-radius: 4px; padding: 1px 5px;
}
[data-theme="dark"] .edo-alert code { background: rgba(255,255,255,.1) }

/* ── Body ──────────────────────────────────────────────────────────────────── */
.edo-body { padding: 16px; display: flex; flex-direction: column; gap: 16px; flex:1 }

.edo-section-lbl {
    font-size: 10px; font-weight: 700; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: .07em;
}

/* ── KPI Grid ──────────────────────────────────────────────────────────────── */
.kpi-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px }

.kpi-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 14px;
    box-shadow: var(--shadow-sm);
    display: flex; flex-direction: column; gap: 5px;
    position: relative; overflow: hidden;
    transition: box-shadow .2s, background .25s, border-color .25s;
}
.kpi-card::before {
    content: "";
    position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: var(--kc, var(--teal));
    border-radius: var(--radius) var(--radius) 0 0;
}
.kpi-card:hover { box-shadow: var(--shadow) }
.kpi-card.amber { --kc: var(--amber) }
.kpi-card.green { --kc: var(--green) }
.kpi-card.blue  { --kc: var(--blue)  }
.kpi-card.purple{ --kc: var(--purple) }
.kpi-card.muted { --kc: var(--text-muted) }

.kpi-ico   { font-size: 20px; line-height: 1 }
.kpi-val   { font-size: 24px; font-weight: 800; color: var(--kc, var(--teal)); line-height: 1 }
.kpi-lbl   { font-size: 10px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .04em }
.kpi-sub   { font-size: 11px; color: var(--text-light) }

/* ── Cards ─────────────────────────────────────────────────────────────────── */
.edo-row      { display: grid; gap: 12px }
.edo-row.two  { grid-template-columns: 1fr 1fr }

.edo-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow-sm);
    overflow: hidden;
    transition: background .25s, border-color .25s;
}
.card-head {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 10px;
    background: var(--surface2);
}
.card-head h3 { font-size: 12px; font-weight: 700; color: var(--text) }
.card-head .ico {
    width: 28px; height: 28px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 14px; background: var(--teal-pale);
}
.card-body { padding: 14px }

/* ── Table ─────────────────────────────────────────────────────────────────── */
.edo-tbl { width: 100%; border-collapse: collapse; font-size: 12px }
.edo-tbl th {
    padding: 8px 10px; color: var(--text-muted);
    font-size: 10px; text-transform: uppercase; letter-spacing: .05em;
    border-bottom: 2px solid var(--border);
    text-align: left; background: var(--surface2);
}
.edo-tbl td {
    padding: 9px 10px;
    border-bottom: 1px solid var(--border);
    color: var(--text);
}
.edo-tbl tr:last-child td { border-bottom: 0 }
.edo-tbl tr:hover td { background: var(--teal-pale) }
.cost { color: var(--amber); font-weight: 700 }

.pill {
    display: inline-flex; align-items: center;
    padding: 2px 8px; border-radius: 999px; font-size: 10px; font-weight: 600;
}
.pill.teal  { background: var(--teal-pale);   color: var(--teal-dark) }
.pill.blue  { background: var(--blue-pale);   color: #1e40af }
.pill.green { background: var(--green-pale);  color: #065f46 }
.pill.amber { background: var(--amber-pale);  color: #92400e }

/* ── Bars ──────────────────────────────────────────────────────────────────── */
.bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px }
.bar-row:last-child { margin-bottom: 0 }
.bar-lbl  { width: 90px; font-size: 11px; color: var(--text-muted); flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap }
.bar-track{ flex: 1; height: 8px; background: var(--border); border-radius: 999px; overflow: hidden }
.bar-fill { height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--teal), var(--teal-light)); transition: width .6s }
.bar-num  { width: 36px; font-size: 11px; font-weight: 700; text-align: right; flex-shrink: 0 }

/* ── Sparkline ─────────────────────────────────────────────────────────────── */
#edo-spark { width: 100%; height: 88px; display: block }

/* ── Empty ─────────────────────────────────────────────────────────────────── */
.edo-empty { padding: 28px; text-align: center; color: var(--text-muted); font-size: 13px }
.edo-empty .e-ico { font-size: 34px; margin-bottom: 10px }

/* ── Responsive ────────────────────────────────────────────────────────────── */
@media(max-width:860px) {
    .kpi-grid { grid-template-columns: repeat(2,1fr) }
    .edo-row.two { grid-template-columns: 1fr }
}
@media(max-width:480px) {
    .kpi-grid { grid-template-columns: 1fr 1fr }
    .edo-body { padding: 10px }
    .kpi-val  { font-size: 20px }
}
</style>
</head>
<body>
<div id="edo-admin">

    <div class="edo-body">

        <!-- ══ ALERTE tables absentes ══════════════════════════════════════ -->
        <?php if (!$has_usage_logs || !$has_conversations): ?>
        <div class="edo-alert">
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24" style="flex-shrink:0;margin-top:1px">
                <path stroke="currentColor" stroke-width="2" stroke-linecap="round"
                      d="M12 9v4m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            </svg>
            <span>
                <?php if (!$has_usage_logs && !$has_conversations): ?>
                    Tables <code>edora_usage_logs</code> et <code>edora_conversations</code> introuvables.
                <?php elseif (!$has_usage_logs): ?>
                    Table <code>edora_usage_logs</code> introuvable — données de coûts API indisponibles.
                <?php else: ?>
                    Table <code>edora_conversations</code> introuvable — statistiques pédagogiques indisponibles.
                <?php endif; ?>
                Réinstallez le plugin depuis <strong>Administration → Plugins → Vue d'ensemble des plugins</strong>.
            </span>
        </div>
        <?php endif; ?>

        <!-- ══ KPIs PLATEFORME ═════════════════════════════════════════════ -->
        <div class="edo-section-lbl">Vue globale plateforme</div>
        <div class="kpi-grid">

            <div class="kpi-card blue">
                <div class="kpi-ico">👥</div>
                <div class="kpi-val"><?= number_format($total_users) ?></div>
                <div class="kpi-lbl">Utilisateurs actifs</div>
            </div>

            <div class="kpi-card green">
                <div class="kpi-ico">📚</div>
                <div class="kpi-val"><?= number_format($total_courses) ?></div>
                <div class="kpi-lbl">Cours visibles</div>
                <div class="kpi-sub"><?= $total_courses_active ?> avec Edora</div>
            </div>

            <div class="kpi-card">
                <div class="kpi-ico">🦉</div>
                <div class="kpi-val"><?= number_format($total_students) ?></div>
                <div class="kpi-lbl">Étudiants Edora</div>
                <div class="kpi-sub"><?= number_format($total_conversations) ?> conversations</div>
            </div>

            <div class="kpi-card amber">
                <div class="kpi-ico">⚡</div>
                <div class="kpi-val"><?= number_format((int)$global->calls_count) ?></div>
                <div class="kpi-lbl">Appels API IA</div>
                <div class="kpi-sub">$<?= number_format((float)$global->cost_usd, 4) ?> total</div>
            </div>

        </div>

        <!-- ══ KPIs TOKENS ════════════════════════════════════════════════ -->
        <div class="edo-section-lbl">Consommation API Gemini</div>
        <div class="kpi-grid">

            <div class="kpi-card">
                <div class="kpi-ico">📥</div>
                <div class="kpi-val"><?= number_format((int)$global->tokens_in) ?></div>
                <div class="kpi-lbl">Tokens IN</div>
            </div>

            <div class="kpi-card">
                <div class="kpi-ico">📤</div>
                <div class="kpi-val"><?= number_format((int)$global->tokens_out) ?></div>
                <div class="kpi-lbl">Tokens OUT</div>
            </div>

            <div class="kpi-card amber">
                <div class="kpi-ico">💰</div>
                <div class="kpi-val">$<?= number_format((float)$global->cost_usd, 4) ?></div>
                <div class="kpi-lbl">Coût total USD</div>
            </div>

            <div class="kpi-card muted">
                <div class="kpi-ico">📊</div>
                <div class="kpi-val">
                    <?= $global->calls_count > 0
                        ? '$' . number_format((float)$global->cost_usd / (int)$global->calls_count, 6)
                        : '—' ?>
                </div>
                <div class="kpi-lbl">Coût / appel</div>
            </div>

        </div>

        <!-- ══ ACTIVITÉ + TÂCHES ══════════════════════════════════════════ -->
        <div class="edo-row two">

            <div class="edo-card">
                <div class="card-head">
                    <div class="ico">📈</div>
                    <h3>Activité — 14 derniers jours</h3>
                </div>
                <div class="card-body">
                    <?php if (!$has_conversations || empty($recent_activity)): ?>
                        <div class="edo-empty"><div class="e-ico">📭</div>Aucune activité enregistrée</div>
                    <?php else: ?>
                        <canvas id="edo-spark"></canvas>
                    <?php endif; ?>
                </div>
            </div>

            <div class="edo-card">
                <div class="card-head">
                    <div class="ico">🎯</div>
                    <h3>Types d'interactions</h3>
                </div>
                <div class="card-body">
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
                            <div class="bar-lbl"><?= $icon ?> <?= s($label) ?></div>
                            <div class="bar-track"><div class="bar-fill" style="width:<?= $pct ?>%"></div></div>
                            <div class="bar-num"><?= number_format((int)$task->nb) ?></div>
                        </div>
                        <?php endforeach; ?>
                    <?php endif; ?>
                </div>
            </div>

        </div>

        <!-- ══ TOP COURS pédagogique ══════════════════════════════════════ -->
        <?php if ($has_conversations && !empty($top_courses)): ?>
        <div class="edo-card">
            <div class="card-head">
                <div class="ico">🏆</div>
                <h3>Cours les plus actifs (Edora)</h3>
            </div>
            <div class="card-body" style="padding:0">
                <table class="edo-tbl">
                    <thead><tr><th>Cours</th><th>Conversations</th><th>Étudiants</th></tr></thead>
                    <tbody>
                    <?php foreach ($top_courses as $row): ?>
                        <tr>
                            <td><?= s($row->fullname ?: 'Cours #' . $row->course_id) ?></td>
                            <td><span class="pill teal"><?= number_format((int)$row->nb_conversations) ?></span></td>
                            <td><span class="pill blue"><?= number_format((int)$row->nb_etudiants) ?></span></td>
                        </tr>
                    <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        </div>
        <?php endif; ?>

        <!-- ══ TOP COURS API ══════════════════════════════════════════════ -->
        <?php if ($has_usage_logs && !empty($bycourse_usage)): ?>
        <div class="edo-card">
            <div class="card-head">
                <div class="ico">💸</div>
                <h3>Consommation API par cours</h3>
            </div>
            <div class="card-body" style="padding:0">
                <table class="edo-tbl">
                    <thead>
                        <tr><th>Cours</th><th>Appels</th><th>Tokens IN</th><th>Tokens OUT</th><th>Coût USD</th></tr>
                    </thead>
                    <tbody>
                    <?php foreach ($bycourse_usage as $row): ?>
                        <tr>
                            <td><?= s($row->fullname ?: 'Cours #' . $row->course_id) ?></td>
                            <td><?= number_format((int)$row->calls_count) ?></td>
                            <td><?= number_format((int)$row->tokens_in) ?></td>
                            <td><?= number_format((int)$row->tokens_out) ?></td>
                            <td class="cost">$<?= number_format((float)$row->cost_usd, 6) ?></td>
                        </tr>
                    <?php endforeach; ?>
                    </tbody>
                </table>
            </div>
        </div>
        <?php endif; ?>

        <!-- ══ ÉTAT VIDE TOTAL ════════════════════════════════════════════ -->
        <?php if (!$has_usage_logs && !$has_conversations): ?>
        <div class="edo-card">
            <div class="card-body">
                <div class="edo-empty">
                    <div class="e-ico">🦉</div>
                    <div style="font-size:15px;font-weight:700;margin-bottom:6px">Edora est prêt</div>
                    <div>Les statistiques apparaîtront dès que des étudiants utiliseront l'assistant IA.</div>
                </div>
            </div>
        </div>
        <?php endif; ?>

    </div><!-- /edo-body -->
</div><!-- /edo-admin -->

<?php if (!empty($chart_labels)): ?>
<script>
(function(){
    var canvas = document.getElementById('edo-spark');
    if (!canvas) return;

    var cs     = getComputedStyle(document.documentElement);
    var get    = function(v){ return cs.getPropertyValue(v).trim(); };

    var ctx    = canvas.getContext('2d');
    var labels = <?= json_encode($chart_labels) ?>;
    var values = <?= json_encode($chart_values) ?>;
    if (!values.length) return;

    var dpr = window.devicePixelRatio || 1;
    var W   = canvas.offsetWidth  || 300;
    var H   = 88;
    canvas.width        = W * dpr;
    canvas.height       = H * dpr;
    canvas.style.width  = W + 'px';
    canvas.style.height = H + 'px';
    ctx.scale(dpr, dpr);

    var maxV = Math.max.apply(null, values) || 1;
    var pad  = { top:8, right:8, bottom:20, left:32 };
    var cW   = W - pad.left - pad.right;
    var cH   = H - pad.top  - pad.bottom;
    var step = cW / Math.max(values.length - 1, 1);

    var pts = values.map(function(v, i){
        return { x: pad.left + i * step, y: pad.top + cH - (v / maxV) * cH };
    });

    var grad = ctx.createLinearGradient(0, pad.top, 0, H - pad.bottom);
    grad.addColorStop(0, get('--spark-f0') || 'rgba(10,147,150,.25)');
    grad.addColorStop(1, get('--spark-f1') || 'rgba(10,147,150,.02)');

    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    pts.forEach(function(p, i){ if (i > 0) ctx.lineTo(p.x, p.y); });
    ctx.lineTo(pts[pts.length-1].x, H - pad.bottom);
    ctx.lineTo(pts[0].x, H - pad.bottom);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    ctx.beginPath();
    ctx.moveTo(pts[0].x, pts[0].y);
    pts.forEach(function(p, i){ if (i > 0) ctx.lineTo(p.x, p.y); });
    ctx.strokeStyle = get('--spark-stroke') || '#0a9396';
    ctx.lineWidth   = 2;
    ctx.lineJoin    = 'round';
    ctx.stroke();

    pts.forEach(function(p){
        ctx.beginPath();
        ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
        ctx.fillStyle = get('--spark-stroke') || '#0a9396';
        ctx.fill();
    });

    var lc = get('--spark-label') || '#94a3b8';
    ctx.fillStyle = lc;
    ctx.font      = '9px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText(maxV, pad.left - 4, pad.top + 8);
    ctx.textAlign = 'center';
    labels.forEach(function(l, i){
        if (i % 3 === 0) ctx.fillText(l, pts[i].x, H - 4);
    });
})();
</script>
<?php endif; ?>

</body>
</html>
<?php
// On arrête ici — pas de $OUTPUT->footer()
exit;