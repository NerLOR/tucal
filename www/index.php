<?php
require ".php/session.php";
require ".php/main.php";
require ".php/header.php";
?>
<main class="w3">
    <section lang="de-AT">
        <h1>TUcal – ein einheitlicher Kalender für die TU Wien</h1>
        <p class="center">
            Dieses Projekt befindet sich noch in der Entwicklungsphase und ist derzeit
            <b>nicht (vollständig) funktionsfähig</b>.
            <br/>
            Der Quellcode ist auf <a href="https://github.com/NerLOR/tucal">GitHub</a> zu finden.
        </p>
        <p>
            Alle Studenten an der <a href="https://www.tuwien.at/">TU Wien</a> kennen folgendes Problem: Jede LVA hat
            einen mehr oder weniger unterschiedlichen Zugang Termine, Deadlines und Änderungen ebendieser an Studenten
            zu kommunizieren. Die Idee von TUcal ist es eine Website zu schaffen, auf der mit einem Blick alle Termine,
            Deadlines uns sonstige terminliche Informationen einer jeden LVA gesammelt zu finden sind. Die Daten hierfür
            sollen automatisiert aus <a href="https://tiss.tuwien.ac.at/">TISS</a> und
            <a href="https://tuwel.tuwien.ac.at/">TUWEL</a> synchronisiert werden. Weiters sollen Studenten die Termine
            bearbeiten können, um eventuell falsche Informationen zu korrigieren.
        </p>
    </section>
    <section lang="de-AT">
        <h1>Benutzerzahlen</h1>
        <?php
        $stmt = db_exec("
            SELECT COUNT(*),
                   SUM(sso_credentials::int),
                   SUM((active_ts >= current_date - INTERVAL '7' DAY)::int),
                   SUM((active_ts >= current_date)::int)
            FROM tucal.v_account WHERE verified = TRUE");
        $row = $stmt->fetchAll()[0];
        $userNum = $row[0];
        $credNum = $row[1];
        $weeklyNum = $row[2];
        $todayNum = $row[3];
        ?>
        <h2>Heute aktiv: <?php echo $todayNum;?></h2>
        <h2>In den letzten 7 Tagen aktiv: <?php echo $weeklyNum;?></h2>
        <h2>SSO-Zugangsdaten hinterlegt: <?php echo $credNum;?></h2>
        <h2>Insgesamt verifiziert: <?php echo $userNum;?></h2>
    </section>
</main>
<?php
require ".php/footer.php";
