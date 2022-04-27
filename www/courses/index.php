<?php

global $TITLE;
global $USER;
global $LOCALE;
global $CONFIG;

require "../.php/session.php";
force_user_login();
require "../.php/main.php";

$TITLE = [_('My Courses')];
require "../.php/header.php";

function echoCourse($course) {
    global $LOCALE;

    $cnr = substr($course['course_nr'], 0, 3) . '.' . substr($course['course_nr'], 3);
    $fullName = in_array($LOCALE, ['bar-AT', 'de-AT', 'de-DE']) ? $course['name_de'] : $course['name_en'];
    $name = htmlspecialchars($course['acronym_1'] ?? $course['acronym_2'] ?? $course['short'] ?? $fullName);
    $fullName = htmlspecialchars($fullName);

    echo "<hr/><a id='$course[course_nr]-$course[semester]' class='anchor'></a><div>";

    echo "<h2><span class='course-name'>$name</span> " .
        "<span class='course-type'>($course[type])</span> " .
        "<span class='course-nr'>$cnr ($course[semester])</span> " .
        "<a href='https://tiss.tuwien.ac.at/course/educationDetails.xhtml?semester=$course[semester]&courseNr=$course[course_nr]' class='link' target='_blank'>TISS</a> ";

    if ($course['course_id']) {
        echo "<a href='https://tuwel.tuwien.ac.at/course/view.php?id=$course[course_id]' class='link' target='_blank'>TUWEL</a> ";
    }

    echo "</h2>\n";
    echo "<h3>$fullName ($course[ects] ECTS)</h3>\n";

    $ignFrom = $course['ignore_from'];
    $ignUntil = $course['ignore_until'];
    if ($ignFrom !== null) {
        $ignFrom = substr($ignFrom, 0, 10);
    }
    if ($ignUntil !== null) {
        $ignUntil = substr($ignUntil, 0, 10);
    }

    if ($ignFrom === null && $ignUntil === null) {
        $mode = 'never';
    } elseif ($ignFrom === '0001-01-01') {
        $mode = 'fully';
        $ignFrom = null;
        $ignUntil = null;
    } else {
        $mode = 'partly';
    }

    ?>
    <form method="post" action="/courses/update">
        <div class="ignore-mode">
            <label><input type="radio" name="ignore" value="never"<?php echo $mode === 'never' ? ' checked': ''; ?>/> <?php echo _('Never ignored'); ?></label>
            <label><input type="radio" name="ignore" value="partly"<?php echo $mode === 'partly' ? ' checked': ''; ?>/> <?php echo _('Partly ignored'); ?></label>
            <label><input type="radio" name="ignore" value="fully"<?php echo $mode === 'fully' ? ' checked': ''; ?>/> <?php echo _('Fully ignored'); ?></label>
        </div>
        <div class="ignore-dates<?php echo $mode === 'partly' ? ' show' : ''; ?>">
            <label><span><?php echo _('Ignore until'); ?></span> <input type="date" name="ignore-until" value="<?php echo $ignUntil; ?>"/></label>
            <label><span><?php echo _('Ignore from'); ?></span> <input type="date" name="ignore-from" value="<?php echo $ignFrom; ?>"/></label>
        </div>
        <input type="hidden" name="course" value="<?php echo "$course[course_nr]-$course[semester]"; ?>"/>
        <button type="submit"><?php echo _('Save'); ?></button>
    </form>
<?php

    foreach ($course['groups'] as $group) {
        echo "$group<br/>";
    }

    echo "</div>\n";
}


$stmt = db_exec("
        SELECT c.course_nr, c.semester, c.ects, cd.name_de, cd.name_en, cd.type, ca.acronym_1, ca.acronym_2,
               ca.short, m.name, m.ignore_until, m.ignore_from, m.group_id, tc.course_id
        FROM tucal.v_account_group m
            JOIN tiss.course c ON (c.course_nr, c.semester) = (m.course_nr, m.semester)
            JOIN tiss.course_def cd ON cd.course_nr = c.course_nr
            LEFT JOIN tucal.course_acronym ca ON ca.course_nr = c.course_nr
            LEFT JOIN tuwel.course tc ON (tc.course_nr, tc.semester) = (m.course_nr, m.semester)
        WHERE account_nr = :nr
        ORDER BY c.semester DESC, c.course_nr", [
    'nr' => $USER['nr']
]);

$maxSem = null;
$last = null;
$courses = [];
while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
    $new = ($row['course_nr'] . '-' . $row['semester'] !== $last);
    if ($row['semester'] > $maxSem) {
        $maxSem = $row['semester'];
    }

    if ($new) {
        $row['groups'] = [];
        $courses[] = $row;
    }

    if ($row['name'] !== 'LVA') {
        $courses[sizeof($courses) - 1]['groups'][] = $row['name'];
    }

    $last = $row['course_nr'] . '-' . $row['semester'];
}

$stmt = db_exec("
        SELECT g.group_nr, group_id, group_name, m.account_nr IS NOT NULL
        FROM tucal.group g
            LEFT JOIN tucal.group_member m ON m.group_nr = g.group_nr AND m.account_nr = :nr
        WHERE public = TRUE", ['nr' => $USER['nr']]);

$groups = [];
while ($row = $stmt->fetch(PDO::FETCH_NUM)) {
    $groups[] = [
        'nr' => $row[0],
        'id' => $row[1],
        'name' => $row[2],
        'member' => $row[3],
    ];
}

$github = 'https://github.com/NerLOR/tucal/blob/master/data/course_acronyms.csv';
$mailto = $CONFIG['email']['contact_direct'] . '?subject=Vorschlag für LVA-Abkürzug(en) bei TUcal';
$contact = '/contact?subject=LVA-Abkürzungen';

?>
<main class="w2">
    <section class="course-list">
        <h1><?php echo _('My Courses'); ?></h1>
        <p class="center small narrow"><?php echo sprintf(_('Course acronym suggestion (description)'), $contact, $mailto, $github); ?></p>
        <?php foreach ($courses as $course) if ($course['semester'] == $maxSem) echoCourse($course); ?>
    </section>
    <section class="group-list">
        <h1><?php echo _('Public Groups'); ?></h1>
        <form action="/courses/update-membership" method="post" class="groups">
            <table>
                <tr>
                    <th><?php echo _('Group'); ?></th>
                    <th><?php echo _('Member'); ?></th>
                </tr>
<?php foreach ($groups as $group) { ?>
    <tr>
        <td><?php echo htmlentities($group['name']); ?></td>
        <td><input type="checkbox" name="group-<?php echo $group['id']; ?>" value="member"<?php if ($group['member']) echo " checked"; ?>/></td>
    </tr>
<?php } ?>
            </table>
            <button type="submit"><?php echo _('Save'); ?></button>
        </form>
    </section>
    <section class="course-list">
        <h1><?php echo _('Old Courses'); ?></h1>
        <?php foreach ($courses as $course) if ($course['semester'] != $maxSem) echoCourse($course); ?>
    </section>
</main>
<?php
require "../.php/footer.php";
