<?php

global $TITLE;
global $USER;

require "../.php/session.php";
force_user_login();

$TITLE = [_('LVAs')];

require "../.php/main.php";
require "../.php/header.php";
?>
<main class="w2">
    <section class="course-list">
        <h1><?php echo _('LVAs');?></h1>
        <?php

        $stmt = db_exec("
                    SELECT c.course_nr, c.semester, c.ects, cd.name_de, cd.type, ca.acronym_1, ca.acronym_2,
                           ca.short, m.name, m.ignore_until, m.ignore_from, m.group_id, tc.course_id
                    FROM tucal.v_account_group m
                        JOIN tiss.course c ON (c.course_nr, c.semester) = (m.course_nr, m.semester)
                        JOIN tiss.course_def cd ON cd.course_nr = c.course_nr
                        JOIN tucal.course_acronym ca ON ca.course_nr = c.course_nr
                        LEFT JOIN tuwel.course tc ON (tc.course_nr, tc.semester) = (m.course_nr, m.semester)
                    WHERE account_nr = :nr", [
            'nr' => $USER['nr']
        ]);
        $last = null;
        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
            $new = ($row['course_nr'] . '-' . $row['semester'] !== $last);
            if ($new) {
                if ($last !== null) echo "</div>\n";
                echo "<hr/><div>";

                $cnr = substr($row['course_nr'], 0, 3) . '.' . substr($row['course_nr'], 3);
                $name = htmlspecialchars($row['acronym_1'] ?? $row['acronym_2'] ?? $row['short'] ?? $row['name_de']);
                $fullName = htmlspecialchars($row['name_de']);

                echo "<h2><span class='course-name'>$name</span> " .
                     "<span class='course-type'>($row[type])</span> " .
                     "<span class='course-nr'>$cnr ($row[semester])</span> " .
                     "<a href='https://tiss.tuwien.ac.at/course/educationDetails.xhtml?semester=$row[semester]&courseNr=$row[course_nr]' class='link' target='_blank'>TISS</a> ";

                if ($row['course_id']) {
                    echo "<a href='https://tuwel.tuwien.ac.at/course/view.php?id=$row[course_id]' class='link' target='_blank'>TUWEL</a> ";
                }

                echo "</h2>\n";
                echo "<h3>$fullName ($row[ects] ECTS)</h3>\n";
            }

            if ($row['name'] !== 'LVA') {
                echo "$row[name]<br/>\n";
            }

            $last = $row['course_nr'] . '-' . $row['semester'];
        }
        if ($last !== null) echo "</div>\n";

        ?>
    </section>
    <section>
        <h1><?php echo _('Groups');?></h1>
        <?php

        $stmt = db_exec("
                    SELECT *
                    FROM tucal.v_account_group
                    WHERE account_nr = :nr AND course_nr IS NULL", [
            'nr' => $USER['nr']
        ]);
        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
            echo "<hr/><div>";
            echo "<h2><span class='course-name'>$row[name]</span></h2>";
            echo "</div>\n";
        }

        ?>
        <hr/>
        <h1><?php echo _('Join Groups');?></h1>
        <?php

        $stmt = db_exec("
                    SELECT *
                    FROM tucal.group g 
                        LEFT JOIN tucal.group_link gl ON gl.group_nr = g.group_nr
                    WHERE gl.course_nr IS NULL");
        while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
            echo "<hr/><div>";
            echo "<h2><span class='course-name'>$row[name]</span></h2>";
            echo "</div>\n";
        }

        ?>
    </section>
</main>
<?php
require "../.php/footer.php";
