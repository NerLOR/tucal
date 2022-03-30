<?php
global $CONFIG;
$emailDirect = $CONFIG['email']['contact_direct'];
$email = $CONFIG['email']['contact'];
$hostname = $CONFIG['tucal']['hostname'];
$contact = "https://$hostname/contact";
?>
<p class="legal">
    Informationspflicht laut
    <a href="https://www.ris.bka.gv.at/NormDokument.wxe?Abfrage=Bundesnormen&Gesetzesnummer=20001703&Paragraf=5" target="_blank">
        <strong>§5&nbsp;ECG</strong>
    </a>
    (<a href="https://www.ris.bka.gv.at/GeltendeFassung.wxe?Abfrage=Bundesnormen&Gesetzesnummer=20001703" target="_blank">E-Commerce-Gesetz</a>)
    und Offenlegungspflicht laut
    <a href="https://www.ris.bka.gv.at/NormDokument.wxe?Abfrage=Bundesnormen&Gesetzesnummer=10000719&Paragraf=25" target="_blank">
        <strong>§25&nbsp;MedienG</strong>
    </a>
    (<a href="https://www.ris.bka.gv.at/GeltendeFassung.wxe?Abfrage=Bundesnormen&Gesetzesnummer=10000719" target="_blank">Mediengesetz</a>).
</p>
<p>
    <strong>Inhaber und Betreiber von TUcal (<a href="https://<?php echo $hostname; ?>/"><?php echo $hostname; ?></a>):</strong>
</p>
<p class="info">
    <strong>Max Mustermann</strong><br/>
    <br/>
    Musterstraße 1,<br/>
    9999 Musterort,<br/>
    Österreich (Austria)<br/>
    <br/>
    E-Mail: <a href="mailto:<?php echo $emailDirect; ?>"><?php echo $email; ?></a><br/>
    Kontakt: <a href="<?php echo $contact; ?>"><?php echo $contact; ?></a>
</p>
