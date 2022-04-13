<?php

global $USER;
global $STATUS;
global $TITLE;

require "../.php/session.php";

force_user_login();
if (!$USER['administrator']) $STATUS = 403;
require "../.php/main.php";

$stmt = db_exec("SELECT * FROM tucal.v_account ORDER BY account_nr;");
$accounts = [];
while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
    $accounts[] = $row;
}

$fmt1 = 'd.m.Y';
$fmt2 = 'd.m.Y, H:i (P)';
$now = time();
$now12 = $now - 12 * 60 * 60;

$TITLE = [_('Accounts'), _('Admin Panel')];
require "../.php/header.php";
?>
<main class="w4">
    <section class="admin">
        <h1><?php echo _('Accounts'); ?></h1>
        <div class="center">
            <a class="button margin" href="/admin/"><?php echo _('Back'); ?></a>
        </div>
        <table>
            <thead>
            <tr>
                <th><?php echo _('Nr.'); ?></th>
                <th><?php echo _('ID'); ?></th>
                <th><?php echo _('Username'); ?></th>
                <th><?php echo _('MNr.'); ?></th>
                <th><?php echo _('Email address'); ?></th>
                <th><?php echo _('Verified'); ?></th>
                <th><?php echo _('Admin'); ?></th>
                <th><?php echo _('SSO'); ?></th>
                <th><?php echo _('Create TS'); ?></th>
                <th><?php echo _('Login TS'); ?></th>
                <th><?php echo _('Active TS'); ?></th>
                <th><?php echo _('Sync TS'); ?></th>
            </tr>
            </thead>
            <tbody>
<?php foreach ($accounts as $a) {
    $ver = $a['verified'] ? _('yes') : _('no');
    $ver_c = $a['verified'] ? 't' : 'f';
    $adm = $a['administrator'] ? _('yes') : _('no');
    $adm_c = $a['administrator'] ? 't' : 'f';
    $sso = $a['sso_credentials'] ? _('yes') : _('no');
    $sso_c = $a['sso_credentials'] ? 't' : 'f';
    $email = substr($a['email_address_1'], 0, 17);
    $create_ts = null;
    $login_ts = null;
    $active_ts = null;
    $sync_ts = null;
    if ($a['create_ts']) $create_ts = strtotime($a['create_ts']);
    if ($a['login_ts']) $login_ts = strtotime($a['login_ts']);
    if ($a['active_ts']) $active_ts = strtotime($a['active_ts']);
    if ($a['sync_ts']) $sync_ts = strtotime($a['sync_ts']);
    $cre1 = $create_ts !== null ? date($fmt1, $create_ts) : _('Never');
    $cre2 = $create_ts !== null ? date($fmt2, $create_ts) : _('Never');
    $log1 = $login_ts !== null ? date($fmt1, $login_ts) : _('Never');
    $log2 = $login_ts !== null ? date($fmt2, $login_ts) : _('Never');
    $act1 = $active_ts !== null ? date($fmt1, $active_ts) : _('Never');
    $act2 = $active_ts !== null ? date($fmt2, $active_ts) : _('Never');
    $syn1 = $sync_ts !== null ? date($fmt1, $sync_ts) : _('Never');
    $syn2 = $sync_ts !== null ? date($fmt2, $sync_ts) : _('Never');
    $act_c = ($active_ts !== null && $active_ts >= $now12) ? 'light' : '';
    $syn_c = ($sync_ts !== null && $sync_ts >= $now12) ? 'light' : '';
    echo "<tr>";
    echo "<td class='nr'>$a[account_nr]</td><td class='id'>$a[account_id]</td>";
    echo "<td><a href='/search?r=users&q=$a[username]'>$a[username]</a></td><td class='nr'>$a[mnr_normal]</td>";
    echo "<td><a href='mailto:$a[email_address_1]'>$email</a></td>";
    echo "<td class='bool $ver_c'>$ver</td><td class='bool $adm_c'>$adm</td><td class='bool $sso_c'>$sso</td>";
    echo "<td class='ts' title='$cre2'>$cre1</td><td class='ts' title='$log2'>$log1</td>";
    echo "<td class='ts $act_c' title='$act2'>$act1</td><td class='ts $syn_c' title='$syn2'><a href='/admin/jobs?mnr=$a[mnr_normal]'>$syn1</a></td>";
    echo "</tr>\n";
} ?>
            </tbody>
        </table>
    </section>
</main>
<?php
require "../.php/footer.php";
