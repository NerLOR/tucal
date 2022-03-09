<?php

global $TITLE;
global $USER;

require "../.php/session.php";
force_user_login();

$TITLE = [_('My Friends')];

require "../.php/main.php";
require "../.php/header.php";
?>
<main class="w2">
    <section>
        <h1><?php echo _('My Friends');?></h1>
        <form action="/search" method="get" class="search">
            <input type="hidden" name="r" value="users"/>
            <input type="text" name="q" placeholder="<?php echo _('Add friend');?>" minlength="3" required/>
            <button type="submit"><?php echo _('Search (for)');?></button>
        </form>
        <div class="friend-container">
<?php

$stmt = db_exec("
        SELECT account_id, mnr, username, f2.nickname, verified
        FROM tucal.friend f1
            JOIN tucal.friend f2 ON (f2.account_nr_1, f2.account_nr_2) = (f1.account_nr_2, f1.account_nr_1)
            JOIN tucal.account a ON a.account_nr = f1.account_nr_1
        WHERE f1.account_nr_2 = :nr
        ORDER BY f2.nickname, a.username", [
    'nr' => $USER['nr'],
]);
while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
    echo '<div>';
    echo_account($row, "/calendar/$row[mnr]/");
    echo "<a href=\"/friends/remove?id=$row[account_id]\" class=\"friend-request\"><img src=\"/res/svgs/\"/></a>";
    echo "</div>\n";
}

?>
        </div>
        <hr/>
        <h2><?php echo _('Pending Friend Requests');?></h2>
        <div class="friend-container">
<?php

$stmt = db_exec("
        SELECT account_id, mnr, username, verified
        FROM tucal.friend f1
            LEFT JOIN tucal.friend f2 ON (f2.account_nr_1, f2.account_nr_2) = (f1.account_nr_2, f1.account_nr_1)
            JOIN tucal.account a ON a.account_nr = f1.account_nr_1
        WHERE f1.account_nr_2 = :nr AND f2.account_nr_1 IS NULL
        ORDER BY a.username", [
    'nr' => $USER['nr'],
]);
while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
    echo '<div>';
    echo_account($row, "/calendar/$row[mnr]/");
    echo "<a href=\"/friends/add?id=$row[account_id]\" class=\"friend-request\"><img src=\"/res/svgs/\"/></a>";
    echo "</div>\n";
}

?>
        </div>
        <hr/>
        <h2><?php echo _('Sent Friend Requests');?></h2>
        <div class="friend-container">
<?php

$stmt = db_exec("
        SELECT account_id, mnr, username, f1.nickname, verified
        FROM tucal.friend f1
            LEFT JOIN tucal.friend f2 ON (f2.account_nr_1, f2.account_nr_2) = (f1.account_nr_2, f1.account_nr_1)
            JOIN tucal.account a ON a.account_nr = f1.account_nr_2
        WHERE f1.account_nr_1 = :nr AND f2.account_nr_1 IS NULL
        ORDER BY f1.nickname, a.username", [
    'nr' => $USER['nr'],
]);
while ($row = $stmt->fetch(PDO::FETCH_ASSOC)) {
    echo '<div>';
    echo_account($row);
    echo "<a href=\"/friends/remove?id=$row[account_id]\" class=\"friend-request\"><img src=\"/res/svgs/\"/></a>";
    echo "</div>\n";
}

?>
        </div>
    </section>
</main>
<?php
require "../.php/footer.php";
