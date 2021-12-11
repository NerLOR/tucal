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
            Alle Studierenden an der <a href="https://www.tuwien.at/">TU Wien</a> kennen folgendes Problem: Jede LVA hat
            einen mehr oder weniger unterschiedlichen Zugang Termine, Deadlines und Änderungen ebendieser an Studierende
            zu kommunizieren. Die Idee von TUcal ist es eine Website zu schaffen, auf der mit einem Blick alle Termine,
            Deadlines uns sonstige terminliche Informationen einer jeden LVA gesammelt zu finden sind. Die Daten hierfür
            sollen automatisiert aus <a href="https://tiss.tuwien.ac.at/">TISS</a> und
            <a href="https://tuwel.tuwien.ac.at/">TUWEL</a> synchronisiert werden. Weiters sollen Studierende die
            Termine bearbeiten können, um eventuell falsche Informationen zu korrigieren.
        </p>
    </section>
</main>
<?php
require ".php/footer.php";
