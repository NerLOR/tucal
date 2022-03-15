<?php

global $TITLE;
global $USER;
global $CONFIG;
global $USE_PATH_INFO;
global $STATUS;

require "../.php/session.php";
force_user_login();

$parts = explode('/', $_SERVER['PATH_INFO']);

$ref = time();
$ref = strtotime((4 - date('N', $ref)) . ' day', $ref);
$year = date('Y', $ref);
$week = 'W' . (int) date('W', $ref);

if (sizeof($parts) < 2 || strlen($parts[1]) === 0)
    redirect("/calendar/$USER[mnr]/$year/$week/");

$subject = $parts[1];
if (sizeof($parts) < 3 || strlen($parts[2]) === 0)
    redirect("/calendar/$subject/$year/$week/");

$year = $parts[2];
if (sizeof($parts) < 5 || strlen($parts[3]) === 0)
    redirect("/calendar/$subject/$year/$week/");

$unit = $parts[3];

if (sizeof($parts) !== 5) {
    $STATUS = 404;
}

if (strlen($year) === 4 && is_numeric($year)) {
    $year = (string) (int) $year;
} else {
    $STATUS = 404;
}

if ($unit[0] === 'W' || $unit[0] === 'w') {
    $week = (int) substr($unit, 1);
    if ($week >= 1 && $week <= 53) {
        $unit = "W$week";
    } else {
        $STATUS = 404;
    }
} elseif (is_numeric($unit)) {
    $month = (int) $unit;
    if ($month >= 1 && $month <= 12) {
        $unit = (string) $month;
    } else {
        $STATUS = 404;
    }
} else {
    $STATUS = 404;
}

$USE_PATH_INFO = true;
require "../.php/main.php";

$wanted_uri = "/calendar/$subject/$year/$unit/$parts[4]";
if ($_SERVER['REQUEST_URI'] !== $wanted_uri) {
    redirect($wanted_uri);
}

$TITLE = [];

if ($subject === $USER['mnr']) {
    $TITLE[] = _('My Calendar');
} else {
    $stmt = db_exec("
            SELECT a.username, f2.nickname
            FROM tucal.friend f1
                JOIN tucal.v_account a ON a.account_nr = f1.account_nr_1
                LEFT JOIN tucal.friend f2 ON f2.account_nr_1 = :nr AND f2.account_nr_2 = f1.account_nr_1
            WHERE (a.mnr, f1.account_nr_2) = (:mnr, :nr)", [
        'mnr' => $subject,
        'nr' => $USER['nr'],
    ]);
    $rows = $stmt->fetchAll(PDO::FETCH_ASSOC);
    if (sizeof($rows) === 0) {
        $STATUS = 403;
    } else {
        $TITLE[] = htmlspecialchars($rows[0]['nickname'] ?? $rows[0]['username']);
    }
    $TITLE[] = _('Calendar');
}


if (!isset($STATUS) || $STATUS === 200) {
    $stmt = db_exec("
            SELECT e.export_nr, e.export_id, e.token, e.account_nr, e.subject_mnr, e.create_ts, e.active_ts, e.options,
                   a.mnr, a.username, f.nickname
            FROM tucal.calendar_export e
                LEFT JOIN tucal.account a ON e.subject_mnr = a.mnr
                LEFT JOIN tucal.friend f ON (f.account_nr_1, f.account_nr_2) = (:nr, a.account_nr)
            WHERE e.account_nr = :nr", [
        'nr' => $USER['nr'],
    ]);
}

require "../.php/header.php";
?>
<main class="wcal">
    <!--Calendar-->
    <section class="calendar-legend">
        <div class="legend lecture">
            <div></div>
            <span class="color-name"><?php echo _('Blue');?></span>
            <span><?php echo _('Lecture');?></span>
        </div>
        <div class="legend course">
            <div></div>
            <span class="color-name"><?php echo _('Purple');?></span>
            <span><?php echo _('General course event');?></span>
        </div>
        <div class="legend group">
            <div></div>
            <span class="color-name"><?php echo _('Green');?></span>
            <span><?php echo _('Group event');?></span>
        </div>
        <div class="legend other">
            <div></div>
            <span class="color-name"><?php echo _('Grey');?></span>
            <span><?php echo _('Other event');?></span>
        </div>
        <div class="legend online">
            <div></div>
            <span class="color-name"><?php echo _('Striped');?></span>
            <span><?php echo _('Online-only event');?></span>
        </div>
        <hr/>
        <div class="button-wrapper">
            <form class="single" action="/calendar/export/add?subject=<?php echo htmlspecialchars($subject);?>" method="post">
                <button type="submit"><?php echo _('Export calendar');?></button>
            </form>
            <a class="button" href="/account/sync"><?php echo _('Synchronize calendar');?></a>
        </div>
    </section>
    <section>
        <h2><?php echo _('Exported calendars');?></h2>
        <div class="calendar-exports-wrapper">
        <table class="calendar-exports">
            <thead>
                <tr><th><?php echo _('User');?></th><th><?php echo _('Link');?></th><th><?php echo _('Settings');?></th><th><?php echo _('Remove');?></th></tr>
            </thead>
            <tbody>
<?php

while ($row = $stmt->fetch()) {
    $path = "/calendar/export/$row[token]/personal.ics";
    $opts = json_decode($row['options'], true);
    $icalOpts = $opts['ical'] ?? [];
    $todos = $icalOpts['todos'] ?? 'as_todos';
    $exportEvents = $icalOpts['event_types'] ?? ['course', 'group'];
    $loc = $icalOpts['location'] ?? 'room_abbr';
    $tuwMaps = $icalOpts['tuw_maps'] ?? true;

?>
    <tr>
        <td>
            <?php echo_account($row, "/calendar/$row[subject_mnr]/");?><br/>
            <?php echo $opts['name'] ?? '';?>
        </td>
        <td><a href="<?php echo $path;?>" class="copy-link"><?php echo _("Open link");?></a></td>
        <td>
            <form action="/calendar/export/update?id=<?php echo $row['export_id'];?>" method="post">
                <div class="flex">
                    <fieldset>
                        <legend><?php echo _('Tasks/Deadlines');?></legend>
                        <label><input type="radio" name="todos" value="omitted"<?php echo ($todos === 'omitted') ? ' checked' : '';?>/> <?php echo _('Do not export');?></label><br/>
                        <label><input type="radio" name="todos" value="as-events"<?php echo ($todos === 'as_events') ? ' checked' : '';?>/> <?php echo _('Export as events');?></label><br/>
                        <label><input type="radio" name="todos" value="as-todos"<?php echo ($todos === 'as_todos') ? ' checked' : '';?>/> <?php echo _('Export as tasks');?></label>
                    </fieldset>
                    <fieldset>
                        <legend><?php echo _('Export events');?></legend>
                        <label><input type="checkbox" name="export-course-events"<?php echo in_array('course', $exportEvents) ? ' checked' : '';?>/> <?php echo _('Course events');?></label><br/>
                        <label><input type="checkbox" name="export-group-events"<?php echo in_array('group', $exportEvents) ? ' checked' : '';?>/> <?php echo _('Group events');?></label><br/>
                        <label><input type="checkbox" name="export-other-events"<?php echo in_array('other', $exportEvents) ? ' checked' : '';?>/> <?php echo _('Other events');?></label>
                    </fieldset>
                    <fieldset>
                        <legend><?php echo _('Event location');?></legend>
                        <label><input type="radio" name="location" value="room-abbr"<?php echo ($loc === 'room_abbr') ? ' checked' : '';?>/> <?php echo _('Room name abbreviation');?></label><br/>
                        <label><input type="radio" name="location" value="room-name"<?php echo ($loc === 'room') ? ' checked' : '';?>/> <?php echo _('Room name');?></label><br/>
                        <label><input type="radio" name="location" value="campus"<?php echo ($loc === 'campus') ? ' checked' : '';?>/> <?php echo _('Campus');?></label><br/>
                        <label><input type="radio" name="location" value="building"<?php echo ($loc === 'building') ? ' checked' : '';?>/> <?php echo _('Building');?></label><br/>
                        <label><input type="radio" name="location" value="full-addr"<?php echo ($loc === 'full_addr') ? ' checked' : '';?>/> <?php echo _('Full address');?></label><br/>
                        <label><input type="checkbox" name="tuw-maps"<?php echo $tuwMaps ? ' checked' : '';?>/> <?php echo _('Include TUW-Maps link');?></label>
                    </fieldset>
                </div>
                <button type="submit"><?php echo _('Save');?></button>
            </form>
        </td>
        <td>
            <form action="/calendar/export/remove?id=<?php echo $row['export_id'];?>" method="post">
                <button type="submit"><?php echo _('Remove');?></button>
            </form>
        </td>
    </tr>
<?php } ?>
            </tbody>
        </table>
        </div>
    </section>
</main>
<?php
require "../.php/footer.php";
