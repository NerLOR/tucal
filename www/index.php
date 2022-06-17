<?php

global $STATUS;
global $LOCALE;

require ".php/session.php";
require ".php/main.php";

try {
    $stmt = db_exec("
            SELECT users_v, users_v_sso, users_v_week, (
                SELECT round(avg(users_v_day))
                FROM tucal.dau
                WHERE date >= tucal.get_today() - INTERVAL '7' DAY AND
                      date != tucal.get_today()
                ), users_v_day
            FROM tucal.v_dau
            WHERE users_v IS NOT NULL
            LIMIT 1");
    $row = $stmt->fetchAll()[0];
    $userNum = $row[0];
    $credNum = $row[1];
    $weeklyNum = $row[2];
    $avgDayNum = $row[3];
    $todayNum = $row[4];
} catch (Exception $e) {
    $STATUS = 500;
    $ERROR = $e->getMessage();
}

$formatter = new NumberFormatter($LOCALE, NumberFormatter::DECIMAL);

require ".php/header.php";
?>
<main class="w3" lang="de-AT">
    <section>
        <h1>TUcal – ein einheitlicher Kalender für die TU Wien</h1>
        <p class="center">
            Dieses Projekt befindet sich noch in der Entwicklungsphase und ist derzeit
            <b>nicht (vollständig) funktionsfähig</b>.
            <br/>
            Der Quellcode ist auf <a href="https://github.com/NerLOR/tucal" target="_blank">GitHub</a> zu finden.
        </p>
        <p>
            Alle Studenten an der <a href="https://www.tuwien.at/" target="_blank">TU Wien</a> kennen folgendes Problem:
            Jede LVA hat einen mehr oder weniger unterschiedlichen Zugang Termine, Deadlines und Änderungen ebendieser
            an Studenten zu kommunizieren. Die Idee von TUcal ist es eine Website zu schaffen, auf der mit einem Blick
            alle Termine, Deadlines uns sonstige terminliche Informationen einer jeden LVA gesammelt zu finden sind. Die
            Daten hierfür sollen automatisiert aus <a href="https://tiss.tuwien.ac.at/" target="_blank">TISS</a> und
            <a href="https://tuwel.tuwien.ac.at/" target="_blank">TUWEL</a> synchronisiert werden. Weiters sollen
            Studenten die Termine bearbeiten können, um eventuell falsche Informationen zu korrigieren.
        </p>
    </section>
    <section class="features">
        <h1>Features</h1>
        <ul>
            <li>
                TISS- und TUWEL-Kalender
                <ul>
                    <li>Synchronisierung im Hintergrund</li>
                    <li>Alle Termine aus deinem <a href="https://tiss.tuwien.ac.at/events/personSchedule.xhtml" target="_blank">TISS-Kalender</a> und <a href="https://tuwel.tuwien.ac.at/calendar/view.php?view=month" target="_blank">TUWEL-Kalender</a></li>
                    <li>Aufgaben und Deadlines aus deinem TUWEL-Kalender inklusive Links zu TUWEL</li>
                    <li>Bei passenden Terminen rechts oben ein Link zu LectureTube oder Zoom</li>
                    <li>Einzelne Termine können im persönlichen Kalender verborgen werden</li>
                    <li>Zum Anzeigen werden LVA-Kürzel verwendet, statt kryptischer LVA-Nummern und ewig langer Namen</li>
                </ul>
            </li>
            <li>
                Konto
                <ul>
                    <li>Per TU-Wien-SSO verifizieren</li>
                    <li>Per <a href="https://mail.student.tuwien.ac.at/webmail/" target="_blank">TU-Wien-Studierenden-E-Mail</a> verifizieren</li>
                    <li>Möglichkeit dein SSO-Passwort verschlüsselt auf dem TUcal-Server zu speichern</li>
                    <li>Sitzungen bis zu 6 Monate gültig, kein ständiges Anmelden erforderlich wie bei TISS/TUWEL/...</li>
                </ul>
            </li>
            <li>
                Nutzbar...
                <ul>
                    <li>...überall im Browser</li>
                    <li>...auf Mobilgeräten als Shortcut auf der Startseite</li>
                </ul>
            </li>
            <li>
                Studi-Schwarmintelligenz
                <ul>
                    <li>Jeder kann Termine editieren</li>
                    <li>Jeder sieht eingetragene Änderungen</li>
                    <li>Termine, die nicht stattfinden, können als abgesagt markiert werden</li>
                </ul>
            </li>
            <li>
                Freunde
                <ul>
                    <li><a href="/account">Profilbild hochladen</a></li>
                    <li><a href="/friends/">Freunde hinzufügen</a></li>
                    <li><a href="/friends/">Kalender deiner Freunde ansehen</a></li>
                </ul>
            </li>
            <li>
                <a href="/courses/#public-groups">Öffentliche Gruppen</a> bzw. <a href="/calendar/tuwien/">Veranstaltungskalender</a>
                <ul>
                    <li>Integrierung von <a href="https://events.htu.at/" target="_blank">events.htu.at</a></li>
                    <li>Integrierung des <a href="https://www.tuwien.at/tu-wien/aktuelles/veranstaltungskalender" target="_blank">Veranstaltungskalenders der TU</a></li>
                </ul>
            </li>
            <li>
                Kalender exportieren
                <ul>
                    <li><a href="/calendar/#exports">Als ICal-Link exportieren</a> und überall verwenden</li>
                </ul>
            </li>
        </ul>
    </section>
    <section class="demo-images">
        <a href="/res/images/demo-1.png" target="_blank"><img src="/res/images/demo-1.png" alt="Demo"/></a>
        <a href="/res/images/demo-2.png" target="_blank"><img src="/res/images/demo-2.png" alt="Demo"/></a>
    </section>
    <section class="stats">
        <h1>Benutzerzahlen</h1>
        <div>
            <div>
                <h2><?php echo $formatter->format($todayNum); ?></h2>
                <h3>Heute aktiv<br/>(ab 04:00)</h3>
            </div>
            <div>
                <h2><?php echo $formatter->format($avgDayNum); ?></h2>
                <h3>Durchschnittlich pro Tag aktiv (7 Tage)</h3>
            </div>
            <div>
                <h2><?php echo $formatter->format($weeklyNum); ?></h2>
                <h3>In den letzten 7 Tagen aktiv</h3>
            </div>
            <div>
                <h2><?php echo $formatter->format($credNum); ?></h2>
                <h3>SSO-Zugangsdaten hinterlegt</h3>
            </div>
            <div>
                <h2><?php echo $formatter->format($userNum); ?></h2>
                <h3>Insgesamt verifiziert</h3>
            </div>
        </div>
    </section>
</main>
<?php
require ".php/footer.php";
