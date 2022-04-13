<?php

global $USER;
global $STATUS;
global $TITLE;

require "../.php/session.php";

force_user_login();
if (!$USER['administrator']) $STATUS = 403;

require "../.php/main.php";

$mnr = $_GET['mnr'] ?? null;

$stmt = db_exec("SELECT * FROM tucal.v_job WHERE mnr = :mnr OR :mnr IS NULL ORDER BY job_nr DESC LIMIT 100", ['mnr' => $mnr]);
$jobs = [];
while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
    $jobs[] = $row;
}

$fmt1 = 'H:i';
$fmt2 = 'd.m.Y, H:i (P)';
$now = time();
$now12 = $now - 12 * 60 * 60;

$TITLE = [_('Jobs'), _('Admin Panel')];
require "../.php/header.php";
?>
<main class="w5">
    <section class="admin">
        <h1><?php echo _('Jobs'); ?></h1>
        <div class="center">
<?php if ($mnr !== null) { ?>
            <a class="button margin" href="/admin/jobs"><?php echo _('Reset'); ?></a>
<?php } ?>
            <a class="button margin" href="<?php echo $_SERVER['REQUEST_URI']; ?>"><?php echo _('Reload'); ?></a>
            <a class="button margin" href="/admin/"><?php echo _('Back'); ?></a>
        </div>
        <table>
            <thead>
            <tr>
                <th><?php echo _('Nr.'); ?></th>
                <th><?php echo _('Id'); ?></th>
                <th><?php echo _('Name'); ?></th>
                <th><?php echo _('PID'); ?></th>
                <th><?php echo _('MNr.'); ?></th>
                <th><?php echo _('Status'); ?></th>
                <th><?php echo _('Error message'); ?></th>
                <th><?php echo _('Start TS'); ?></th>
                <th><?php echo _('ETA TS'); ?></th>
                <th><?php echo _('Time'); ?></th>
                <th><?php echo _('Time remaining'); ?></th>
            </tr>
            </thead>
            <tbody>
<?php foreach ($jobs as $j) {
    $data = json_decode($j['data'], true);
    $start_ts = null;
    $eta_ts = null;
    if ($j['start_ts']) $start_ts = strtotime($j['start_ts']);
    if ($j['eta_ts']) $eta_ts = strtotime($j['eta_ts']);
    $start1 = date($fmt1, $start_ts);
    $start2 = date($fmt2, $start_ts);
    $eta1 = date($fmt1, $eta_ts);
    $eta2 = date($fmt2, $eta_ts);
    $error = $j['error_msg'];
    if ($error === '') $error = $data['error'];
    echo "<tr>";
    echo "<td class='nr'>$j[job_nr]</td><td class='id'>$j[job_id]</td>";
    echo "<td>$j[name]</td><td class='nr'>" . ($j['pid'] ?? '-') . "</td><td class='nr'>" . ($j['mnr'] ?? '-') . "</td>";
    echo "<td>$j[status]</td><td class='scroll'>" . (($error !== null) ? ("<pre>" . htmlentities($error) . "</pre>") : '-') . "</td>";
    echo "<td class='ts' title='$start2'>$start1</td><td class='ts' title='$eta2'>$eta1</td>";
    echo "<td class='nr'>$j[time]</td><td class='nr'>$j[time_remaining]</td>";
    echo "</tr>\n";
} ?>
            </tbody>
        </table>
    </section>
</main>
<?php
require "../.php/footer.php";
