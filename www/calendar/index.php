<?php

global $TITLE;
global $USER;
global $CONFIG;
global $USE_PATH_INFO;
global $STATUS;

require "../.php/session.php";

$parts = explode('/', $_SERVER['PATH_INFO']);

$ref = time();
$ref = strtotime((4 - date('N', $ref)) . ' day', $ref);
$year = date('Y', $ref);
$week = 'W' . (int) date('W', $ref);

if (sizeof($parts) < 2 || strlen($parts[1]) === 0) {
    if (isset($USER)) {
        redirect("/calendar/$USER[mnr]/$year/$week/");
    } else {
        force_user_login();
    }
}

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

if ($subject === 'tuwien') {
    $TITLE[] = _('Veranstaltungen');
    $TITLE[] = _('TU Wien');
} elseif ($subject === 'demo') {
    $STATUS = 501;
} else {
    force_user_login();
    if ($subject === $USER['mnr']) {
        $TITLE[] = _('My Calendar');
    } elseif (is_numeric($subject)) {
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
    } else {
        $STATUS = 404;
    }
}


if (isset($USER) && (!isset($STATUS) || $STATUS === 200)) {
    $stmt = db_exec("
            SELECT e.export_nr, e.export_id, e.token, e.account_nr, e.subject_mnr, e.create_ts, e.active_ts, e.options,
                   a.mnr, a.username, f.nickname
            FROM tucal.calendar_export e
                LEFT JOIN tucal.account a ON e.subject_mnr = a.mnr
                LEFT JOIN tucal.friend f ON (f.account_nr_1, f.account_nr_2) = (:nr, a.account_nr)
            WHERE e.account_nr = :nr
            ORDER BY f.nickname, a.username, e.options->'name'", [
        'nr' => $USER['nr'],
    ]);
}

require "../.php/header.php";
?>
<main class="wcal">
    <!--Calendar-->
    <section class="calendar-legend">
        <div class="legend-wrapper">
            <div>
                <div class="legend lecture explicit">
                    <div></div>
                    <span class="color-name"><?php echo _('Blue'); ?></span>
                    <span><?php echo _('Lecture'); ?></span>
                </div>
                <div class="legend course explicit">
                    <div></div>
                    <span class="color-name"><?php echo _('Purple'); ?></span>
                    <span><?php echo _('General course event'); ?></span>
                </div>
                <div class="legend group explicit">
                    <div></div>
                    <span class="color-name"><?php echo _('Green'); ?></span>
                    <span><?php echo _('Group event'); ?></span>
                </div>
                <div class="legend appointment explicit">
                    <div></div>
                    <span class="color-name"><?php echo _('Orange'); ?></span>
                    <span><?php echo _('Appointment'); ?></span>
                </div>
            </div>
            <div>
                <div class="legend exam explicit">
                    <div></div>
                    <span class="color-name"><?php echo _('Red'); ?></span>
                    <span><?php echo _('Exam'); ?></span>
                </div>
                <div class="legend holiday explicit">
                    <div></div>
                    <span class="color-name"><?php echo _('Yellow'); ?></span>
                    <span><?php echo _('Holiday'); ?></span>
                </div>
                <div class="legend other">
                    <div></div>
                    <span class="color-name"><?php echo _('Grey'); ?></span>
                    <span><?php echo _('Other event'); ?></span>
                </div>
                <div class="legend online">
                    <div></div>
                    <span class="color-name"><?php echo _('Striped'); ?></span>
                    <span><?php echo _('Online-only event'); ?></span>
                </div>
            </div>
        </div>
<?php if (isset($USER) && $subject !== 'tuwien' && $subject !== 'demo') { ?>
        <hr/>
        <div class="button-wrapper">
            <form class="single" action="/calendar/export/add?subject=<?php echo htmlspecialchars($subject); ?>" method="post">
                <button type="submit"><?php echo _('Export calendar'); ?></button>
            </form>
            <a class="button" href="/account/sync"><?php echo _('Synchronize calendar'); ?></a>
        </div>
<?php } ?>
    </section>
<?php if (isset($USER)) { ?>
    <section>
        <h2 id="exports"><?php echo _('Exported calendars'); ?></h2>
        <div class="table-wrapper">
        <table class="calendar-exports">
            <thead>
                <tr><th><?php echo _('Calendar'); ?></th><th><?php echo _('Settings'); ?></th><th><?php echo _('Remove'); ?></th></tr>
            </thead>
            <tbody>
<?php

while ($row = $stmt->fetch()) {
    $path = "/calendar/export/$row[token]/personal.ics";
    $opts = json_decode($row['options'], true);
    $icalOpts = $opts['ical'] ?? [];
    $todos = $icalOpts['todos'] ?? 'as_todos';
    $exportEvents = $icalOpts['event_types'] ?? ['course', 'group', 'appointment', 'exam'];
    $loc = $icalOpts['location'] ?? 'room_abbr';
    $tuwMaps = $icalOpts['tuw_maps'] ?? true;
    $cat = ($icalOpts['categories'] ?? ['event_type'])[0];
    $planned = $icalOpts['planned'] ?? true;

?>
    <tr>
        <td>
            <?php echo_account($row, "/calendar/$row[subject_mnr]/"); ?><br/>
        </td>
        <td rowspan="3">
            <form action="/calendar/export/update?id=<?php echo $row['export_id']; ?>" method="post">
                <div class="flex">
                    <div class="sub-flex">
                        <fieldset>
                            <legend><?php echo _('Tasks/Deadlines'); ?></legend>
                            <label><input type="radio" name="todos" value="omitted"<?php echo ($todos === 'omitted') ? ' checked' : ''; ?>/> <?php echo _('Do not export'); ?></label><br/>
                            <label><input type="radio" name="todos" value="as-events"<?php echo ($todos === 'as_events') ? ' checked' : ''; ?>/> <?php echo _('Export as events'); ?></label><br/>
                            <label><input type="radio" name="todos" value="as-todos"<?php echo ($todos === 'as_todos') ? ' checked' : ''; ?>/> <?php echo _('Export as tasks'); ?></label>
                        </fieldset>
                        <fieldset>
                            <legend><?php echo _('Export events'); ?></legend>
                            <label><input type="checkbox" name="export-course-events"<?php echo in_array('course', $exportEvents) ? ' checked' : ''; ?>/> <?php echo _('Course events'); ?></label><br/>
                            <label><input type="checkbox" name="export-group-events"<?php echo in_array('group', $exportEvents) ? ' checked' : ''; ?>/> <?php echo _('Group events'); ?></label><br/>
                            <label><input type="checkbox" name="export-appointment-events"<?php echo in_array('appointment', $exportEvents) ? ' checked' : ''; ?>/> <?php echo _('Appointments'); ?></label><br/>
                            <label><input type="checkbox" name="export-exam-events"<?php echo in_array('exam', $exportEvents) ? ' checked' : ''; ?>/> <?php echo _('Exams'); ?></label><br/>
                            <label><input type="checkbox" name="export-holiday-events"<?php echo in_array('holiday', $exportEvents) ? ' checked' : ''; ?>/> <?php echo _('Holidays'); ?></label><br/>
                            <label><input type="checkbox" name="export-other-events"<?php echo in_array('other', $exportEvents) ? ' checked' : ''; ?>/> <?php echo _('Other events'); ?></label>
                        </fieldset>
                    </div>
                    <fieldset>
                        <legend><?php echo _('Event location'); ?></legend>
                        <label><input type="radio" name="location" value="room-abbr"<?php echo ($loc === 'room_abbr') ? ' checked' : ''; ?>/> <?php echo _('Room name abbreviation'); ?></label><br/>
                        <label><input type="radio" name="location" value="room-name"<?php echo ($loc === 'room_name') ? ' checked' : ''; ?>/> <?php echo _('Room name'); ?></label><br/>
                        <label><input type="radio" name="location" value="campus"<?php echo ($loc === 'campus') ? ' checked' : ''; ?>/> <?php echo _('Campus'); ?></label><br/>
                        <label><input type="radio" name="location" value="building"<?php echo ($loc === 'building') ? ' checked' : ''; ?>/> <?php echo _('Building'); ?></label><br/>
                        <label><input type="radio" name="location" value="full-addr"<?php echo ($loc === 'full_addr') ? ' checked' : ''; ?>/> <?php echo _('Full address'); ?></label><br/>
                        <label><input type="checkbox" name="tuw-maps"<?php echo $tuwMaps ? ' checked' : ''; ?>/> <?php echo _('Include TUW-Maps link'); ?></label>
                    </fieldset>
                    <div class="sub-flex">
                        <fieldset>
                            <legend><?php echo _('Event categories'); ?></legend>
                            <label><input type="radio" name="categories" value="event-type"<?php echo ($cat === 'event_type' ? ' checked' : ''); ?>/> <?php echo _('By event type'); ?></label><br/>
                            <label><input type="radio" name="categories" value="course"<?php echo ($cat === 'course' ? ' checked' : ''); ?>/> <?php echo _('By course'); ?></label>
                        </fieldset>
                        <fieldset>
                            <label><input type="checkbox" name="planned" <?php echo $planned ? ' checked' : ''?>/> <?php echo _('Use c.t. times'); ?></label>
                        </fieldset>
                        <input type="text" name="name" value="<?php echo htmlentities($opts['name'] ?? ''); ?>" placeholder="<?php echo _('Name'); ?>"/>
                    </div>
                </div>
                <button type="submit"><?php echo _('Save'); ?></button>
            </form>
        </td>
        <td rowspan="3">
            <form action="/calendar/export/remove?id=<?php echo $row['export_id']; ?>" method="post">
                <button type="submit"><?php echo _('Remove'); ?></button>
            </form>
        </td>
    </tr>
    <tr>
        <td><?php echo htmlentities($opts['name'] ?? ''); ?></td>
    </tr>
    <tr>
        <td><a href="<?php echo $path; ?>" class="copy-link"><?php echo _("Open link"); ?></a></td>
    </tr>
<?php } ?>
            </tbody>
        </table>
        </div>
    </section>
<?php } ?>
</main>
<?php
require "../.php/footer.php";
