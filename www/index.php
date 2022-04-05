<?php

global $STATUS;

require ".php/session.php";
require ".php/main.php";

try {
    $stmt = db_exec("
            SELECT users_v, users_v_sso, users_v_week, users_v_day
            FROM tucal.v_dau
            WHERE users_v IS NOT NULL
            LIMIT 1");
    $row = $stmt->fetchAll()[0];
    $userNum = $row[0];
    $credNum = $row[1];
    $weeklyNum = $row[2];
    $todayNum = $row[3];
} catch (Exception $e) {
    $STATUS = 500;
    $ERROR = $e->getMessage();
}

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
    <section lang="de-AT" class="stats">
        <h1>Benutzerzahlen</h1>
        <div>
            <div>
                <h2><?php echo $todayNum; ?></h2>
                <h3>Heute aktiv</h3>
            </div>
            <div>
                <h2><?php echo $weeklyNum; ?></h2>
                <h3>In den letzten 7 Tagen aktiv</h3>
            </div>
            <div>
                <h2><?php echo $credNum; ?></h2>
                <h3>SSO-Zugangsdaten hinterlegt</h3>
            </div>
            <div>
                <h2><?php echo $userNum; ?></h2>
                <h3>Insgesamt verifiziert</h3>
            </div>
        </div>
    </section>
</main>
<?php
require ".php/footer.php";
