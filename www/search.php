<?php

global $TITLE;
global $STATUS;
global $USER;

require ".php/session.php";
force_user_login();

$TITLE = [];
if (isset($_GET['q'])) {
    $TITLE[] = $_GET['q'];
}
$TITLE[] = _('Search');

require ".php/main.php";

$query = $_GET['q'] ?? '';
$r = $_GET['r'] ?? null;

require ".php/header.php";
?>
<main class="w3 search">
    <section>
        <form action="/search" method="get" class="search">
            <input type="text" name="q" placeholder="<?php echo _('Search (for)');?>" value="<?php echo htmlspecialchars($query)?>" minlength="3" required/>
            <button type="submit"><?php echo _('Search (for)');?></button>
        </form>
<?php
if (strlen($query) >= 3) {
    if ($r === null || $r === 'users') {

?>
        <hr/>
        <h2><?php echo _('Students');?></h2>
<?php

        $stmt = db_exec("
                SELECT account_id, mnr, username, verified, account_nr_1 IS NOT NULL AS friend_request
                FROM tucal.v_account a
                    LEFT JOIN tucal.friend f ON (f.account_nr_1, f.account_nr_2) = (:nr, a.account_nr)
                WHERE mnr::text = :q OR
                      username ILIKE CONCAT('%', :q, '%')
                ORDER BY username", ['q' => $query, 'nr' => $USER['nr']]);
        while ($row = $stmt->fetch()) {
            echo "<div>";
            echo_account($row, true);
            if (!$row['friend_request'] && $row['account_id'] !== $USER['id']) {
                echo "<a href=\"/friends/add?id=$row[account_id]\" class=\"friend-request\"><img src=\"/res/svgs/\"/></a>";
            }
            echo "</div>\n";
        }
    }

    if ($r === null || $r === 'courses') {

?>
        <hr/>
        <h2><?php echo _('LVAs');?> (TISS)</h2>
<?php

        $cnr = str_replace('.', '', $query);
        $stmt = db_exec("SELECT * FROM tiss.course_def WHERE course_nr = :cnr::text OR name_de ILIKE CONCAT('%', :q::text, '%') ORDER BY name_de",
            ['q' => $query, 'cnr' => $cnr]);
        while ($row = $stmt->fetch()) {
            echo '<div><div lang="de" class="course">';
            $cnr = substr($row['course_nr'], 0, 3) . '.' . substr($row['course_nr'], 3);
            echo "$cnr $row[name_de] ($row[type])";
            echo "</div></div>\n";
        }
    }
}
?>
    </section>
</main>
<?php
require ".php/footer.php";
