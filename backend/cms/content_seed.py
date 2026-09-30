"""
CMS page content for seed_data.
Draft legal text — client should review with a lawyer before going live.
"""

DRAFT_NOTICE_IT = (
    '<p class="cms-notice"><em>Bozza informativa — da revisionare con un consulente legale prima della pubblicazione.</em></p>'
)
DRAFT_NOTICE_EN = (
    '<p class="cms-notice"><em>Draft notice — review with legal counsel before publishing.</em></p>'
)

PAGE_CONTENT = {
    "about": {
        "title_it": "Chi siamo",
        "title_en": "About Us",
        "meta_it": "SecurWork — abbigliamento da lavoro e professionale in Italia",
        "meta_en": "SecurWork — workwear and professional clothing in Italy",
        "content_it": f"""{DRAFT_NOTICE_IT}
<h2>La nostra missione</h2>
<p>SecurWork è specializzata nella fornitura di <strong>abbigliamento da lavoro</strong> e <strong>abbigliamento professionale</strong> per aziende, artigiani e professionisti in tutta Italia.</p>
<h2>Cosa offriamo</h2>
<ul>
<li>Abbigliamento tecnico e antinfortunistica conforme alle normative</li>
<li>Capo professionale per settori HORECA, sanità, industria e servizi</li>
<li>Consulenza sulla scelta dei prodotti più adatti al vostro settore</li>
<li>Spedizioni in tutta Italia con tempi rapidi</li>
</ul>
<h2>Perché sceglierci</h2>
<p>Qualità dei materiali, rapporto qualità-prezzo competitivo e assistenza clienti dedicata. Ogni prodotto è selezionato per garantire comfort, durata e sicurezza sul luogo di lavoro.</p>
<p><strong>Nota:</strong> sostituire questa sezione con la storia reale dell'azienda, certificazioni e dati societari.</p>""",
        "content_en": f"""{DRAFT_NOTICE_EN}
<h2>Our mission</h2>
<p>SecurWork specialises in <strong>workwear</strong> and <strong>professional clothing</strong> for companies, tradespeople and professionals across Italy.</p>
<h2>What we offer</h2>
<ul>
<li>Technical and safety workwear compliant with regulations</li>
<li>Professional apparel for HORECA, healthcare, industry and services</li>
<li>Advice on choosing the right products for your sector</li>
<li>Fast shipping throughout Italy</li>
</ul>
<h2>Why choose us</h2>
<p>Quality materials, competitive value and dedicated customer support. Every product is selected for comfort, durability and workplace safety.</p>
<p><strong>Note:</strong> replace this section with the company's real story, certifications and corporate details.</p>""",
    },
    "contact": {
        "title_it": "Contatti",
        "title_en": "Contact",
        "meta_it": "Contatta SecurWork — assistenza e informazioni",
        "meta_en": "Contact SecurWork — support and information",
        "content_it": """<p>Per informazioni su prodotti, ordini o preventivi personalizzati, compila il modulo sulla pagina contatti o utilizza i recapiti indicati.</p>
<p>Il nostro team risponde entro <strong>24–48 ore lavorative</strong>.</p>""",
        "content_en": """<p>For product information, orders or custom quotes, use the contact form or the details shown on the contact page.</p>
<p>Our team responds within <strong>1–2 business days</strong>.</p>""",
    },
    "shipping": {
        "title_it": "Spedizioni e consegne",
        "title_en": "Shipping & Delivery",
        "meta_it": "Informazioni sulle spedizioni SecurWork",
        "meta_en": "SecurWork shipping information",
        "content_it": f"""{DRAFT_NOTICE_IT}
<h2>Zone di consegna</h2>
<p>Spediamo in tutta <strong>Italia</strong> (isole comprese). Per spedizioni internazionali, contattaci prima dell'ordine.</p>
<h2>Tempi di elaborazione</h2>
<p>Gli ordini vengono elaborati entro <strong>1–3 giorni lavorativi</strong> dalla conferma del pagamento.</p>
<h2>Tempi di consegna stimati</h2>
<ul>
<li>Italia continentale: 2–5 giorni lavorativi</li>
<li>Sicilia, Sardegna e aree remote: 3–7 giorni lavorativi</li>
</ul>
<h2>Costi di spedizione</h2>
<p>Spedizione standard: <strong>€5,99</strong>. Spedizione <strong>gratuita</strong> per ordini superiori a <strong>€100</strong> (IVA esclusa).</p>
<h2>Tracciamento</h2>
<p>Riceverai un'email con il codice di tracciamento non appena l'ordine viene spedito.</p>""",
        "content_en": f"""{DRAFT_NOTICE_EN}
<h2>Delivery areas</h2>
<p>We ship throughout <strong>Italy</strong> (including islands). For international shipping, please contact us before ordering.</p>
<h2>Processing times</h2>
<p>Orders are processed within <strong>1–3 business days</strong> after payment confirmation.</p>
<h2>Estimated delivery times</h2>
<ul>
<li>Mainland Italy: 2–5 business days</li>
<li>Sicily, Sardinia and remote areas: 3–7 business days</li>
</ul>
<h2>Shipping costs</h2>
<p>Standard shipping: <strong>€5.99</strong>. <strong>Free</strong> shipping on orders over <strong>€100</strong> (excl. VAT).</p>
<h2>Tracking</h2>
<p>You will receive an email with a tracking code once your order has been dispatched.</p>""",
    },
    "returns": {
        "title_it": "Resi e rimborsi",
        "title_en": "Returns & Refunds",
        "meta_it": "Politica resi SecurWork",
        "meta_en": "SecurWork returns policy",
        "content_it": f"""{DRAFT_NOTICE_IT}
<h2>Diritto di recesso</h2>
<p>Hai <strong>14 giorni</strong> dalla consegna per esercitare il diritto di recesso, ai sensi del Codice del Consumo (D.Lgs. 206/2005).</p>
<h2>Condizioni</h2>
<ul>
<li>Il prodotto deve essere integro, non indossato e nella confezione originale</li>
<li>Etichette e cartellini devono essere ancora presenti</li>
<li>Prodotti personalizzati o su misura non sono restituibili salvo difetti</li>
</ul>
<h2>Procedura</h2>
<ol>
<li>Contattaci via email indicando numero ordine e motivo del reso</li>
<li>Attendi conferma e istruzioni per la spedizione di ritorno</li>
<li>Il rimborso viene effettuato entro 14 giorni dalla ricezione del reso</li>
</ol>
<h2>Articoli difettosi</h2>
<p>In caso di difetto di conformità, contattaci entro 2 giorni dalla consegna. Provvederemo alla sostituzione o al rimborso completo, incluse le spese di spedizione.</p>""",
        "content_en": f"""{DRAFT_NOTICE_EN}
<h2>Right of withdrawal</h2>
<p>You have <strong>14 days</strong> from delivery to exercise your right of withdrawal under Italian consumer law (Legislative Decree 206/2005).</p>
<h2>Conditions</h2>
<ul>
<li>Product must be unused, undamaged and in original packaging</li>
<li>Tags and labels must still be attached</li>
<li>Customised or made-to-order items are non-returnable unless defective</li>
</ul>
<h2>Procedure</h2>
<ol>
<li>Contact us by email with your order number and reason for return</li>
<li>Wait for confirmation and return shipping instructions</li>
<li>Refund is issued within 14 days of receiving the return</li>
</ol>
<h2>Defective items</h2>
<p>If you receive a defective item, contact us within 2 days of delivery. We will arrange a replacement or full refund including shipping costs.</p>""",
    },
    "privacy": {
        "title_it": "Privacy Policy",
        "title_en": "Privacy Policy",
        "meta_it": "Informativa sulla privacy — SecurWork",
        "meta_en": "Privacy policy — SecurWork",
        "content_it": f"""{DRAFT_NOTICE_IT}
<h2>Titolare del trattamento</h2>
<p><strong>[PLACEHOLDER — Ragione sociale]</strong><br>
[PLACEHOLDER — Indirizzo sede legale]<br>
P.IVA: [PLACEHOLDER]<br>
Email: info@securwork.it</p>
<h2>Dati raccolti</h2>
<p>Raccogliamo i dati necessari per gestire ordini e richieste: nome, email, indirizzo, telefono, dati di pagamento (gestiti da Stripe).</p>
<h2>Finalità del trattamento</h2>
<ul>
<li>Evasione ordini e spedizioni</li>
<li>Assistenza clienti</li>
<li>Adempimenti fiscali e contabili</li>
<li>Marketing (solo con consenso esplicito)</li>
</ul>
<h2>Base giuridica</h2>
<p>Esecuzione del contratto (art. 6.1.b GDPR), obblighi legali (art. 6.1.c), consenso (art. 6.1.a) per newsletter.</p>
<h2>Conservazione</h2>
<p>I dati degli ordini sono conservati per 10 anni (obblighi fiscali). I dati di contatto per 24 mesi dall'ultima interazione.</p>
<h2>Diritti dell'interessato</h2>
<p>Hai diritto di accesso, rettifica, cancellazione, limitazione, portabilità e opposizione. Contatta info@securwork.it o l'Autorità Garante (<a href="https://www.garanteprivacy.it">garanteprivacy.it</a>).</p>""",
        "content_en": f"""{DRAFT_NOTICE_EN}
<h2>Data controller</h2>
<p><strong>[PLACEHOLDER — Company name]</strong><br>
[PLACEHOLDER — Registered address]<br>
VAT: [PLACEHOLDER]<br>
Email: info@securwork.it</p>
<h2>Data we collect</h2>
<p>We collect data necessary to process orders and enquiries: name, email, address, phone, payment data (processed by Stripe).</p>
<h2>Purposes</h2>
<ul>
<li>Order fulfilment and shipping</li>
<li>Customer support</li>
<li>Tax and accounting obligations</li>
<li>Marketing (only with explicit consent)</li>
</ul>
<h2>Legal basis</h2>
<p>Contract performance (Art. 6.1.b GDPR), legal obligations (Art. 6.1.c), consent (Art. 6.1.a) for newsletter.</p>
<h2>Retention</h2>
<p>Order data is kept for 10 years (tax requirements). Contact data for 24 months from last interaction.</p>
<h2>Your rights</h2>
<p>You have the right to access, rectify, erase, restrict, port and object. Contact info@securwork.it or the Italian Data Protection Authority (<a href="https://www.garanteprivacy.it">garanteprivacy.it</a>).</p>""",
    },
    "cookies": {
        "title_it": "Cookie Policy",
        "title_en": "Cookie Policy",
        "meta_it": "Informativa sui cookie — SecurWork",
        "meta_en": "Cookie policy — SecurWork",
        "content_it": f"""{DRAFT_NOTICE_IT}
<h2>Cosa sono i cookie</h2>
<p>I cookie sono piccoli file di testo salvati sul tuo dispositivo quando visiti un sito web.</p>
<h2>Cookie utilizzati</h2>
<table>
<thead><tr><th>Cookie</th><th>Tipo</th><th>Scopo</th><th>Durata</th></tr></thead>
<tbody>
<tr><td>sessionid</td><td>Tecnico</td><td>Carrello e sessione</td><td>Sessione</td></tr>
<tr><td>csrftoken</td><td>Tecnico</td><td>Sicurezza form</td><td>1 anno</td></tr>
<tr><td>securwork-cookie-consent</td><td>Tecnico</td><td>Preferenza consenso cookie</td><td>1 anno</td></tr>
<tr><td>_stripe_*</td><td>Terze parti</td><td>Pagamenti Stripe</td><td>Variabile</td></tr>
</tbody>
</table>
<h2>Gestione dei cookie</h2>
<p>Puoi gestire i cookie dalle impostazioni del browser. La disattivazione dei cookie tecnici potrebbe limitare alcune funzionalità del sito (es. carrello).</p>
<h2>Cookie di terze parti</h2>
<p>Stripe utilizza cookie per elaborare i pagamenti in modo sicuro. Consulta la <a href="https://stripe.com/privacy">privacy policy di Stripe</a>.</p>""",
        "content_en": f"""{DRAFT_NOTICE_EN}
<h2>What are cookies</h2>
<p>Cookies are small text files stored on your device when you visit a website.</p>
<h2>Cookies we use</h2>
<table>
<thead><tr><th>Cookie</th><th>Type</th><th>Purpose</th><th>Duration</th></tr></thead>
<tbody>
<tr><td>sessionid</td><td>Technical</td><td>Cart and session</td><td>Session</td></tr>
<tr><td>csrftoken</td><td>Technical</td><td>Form security</td><td>1 year</td></tr>
<tr><td>securwork-cookie-consent</td><td>Technical</td><td>Cookie consent preference</td><td>1 year</td></tr>
<tr><td>_stripe_*</td><td>Third party</td><td>Stripe payments</td><td>Variable</td></tr>
</tbody>
</table>
<h2>Managing cookies</h2>
<p>You can manage cookies in your browser settings. Disabling technical cookies may limit site functionality (e.g. cart).</p>
<h2>Third-party cookies</h2>
<p>Stripe uses cookies to process payments securely. See <a href="https://stripe.com/privacy">Stripe's privacy policy</a>.</p>""",
    },
    "terms": {
        "title_it": "Termini e condizioni",
        "title_en": "Terms & Conditions",
        "meta_it": "Termini e condizioni di vendita — SecurWork",
        "meta_en": "Terms and conditions of sale — SecurWork",
        "content_it": f"""{DRAFT_NOTICE_IT}
<h2>1. Oggetto</h2>
<p>Le presenti condizioni regolano la vendita di prodotti tramite il sito www.securwork.it.</p>
<h2>2. Venditore</h2>
<p><strong>[PLACEHOLDER — Ragione sociale]</strong>, P.IVA [PLACEHOLDER], sede in [PLACEHOLDER].</p>
<h2>3. Ordini</h2>
<p>L'ordine si perfeziona con la conferma via email. Ci riserviamo il diritto di annullare ordini in caso di errore di prezzo o indisponibilità.</p>
<h2>4. Prezzi e pagamento</h2>
<p>I prezzi sono in Euro, IVA inclusa dove indicato. Metodi accettati: carta (Stripe) e bonifico bancario.</p>
<h2>5. Spedizione</h2>
<p>Vedi la pagina <a href="/pages/shipping">Spedizioni e consegne</a>.</p>
<h2>6. Resi</h2>
<p>Vedi la pagina <a href="/pages/returns">Resi e rimborsi</a>.</p>
<h2>7. Garanzia</h2>
<p>I prodotti sono coperti dalla garanzia legale di conformità (24 mesi per consumatori).</p>
<h2>8. Legge applicabile</h2>
<p>Legge italiana. Foro competente: [PLACEHOLDER — città sede legale].</p>""",
        "content_en": f"""{DRAFT_NOTICE_EN}
<h2>1. Scope</h2>
<p>These terms govern the sale of products through www.securwork.it.</p>
<h2>2. Seller</h2>
<p><strong>[PLACEHOLDER — Company name]</strong>, VAT [PLACEHOLDER], registered at [PLACEHOLDER].</p>
<h2>3. Orders</h2>
<p>An order is confirmed by email. We reserve the right to cancel orders due to pricing errors or unavailability.</p>
<h2>4. Prices and payment</h2>
<p>Prices are in Euros, VAT included where stated. Accepted methods: card (Stripe) and bank transfer.</p>
<h2>5. Shipping</h2>
<p>See our <a href="/pages/shipping">Shipping & Delivery</a> page.</p>
<h2>6. Returns</h2>
<p>See our <a href="/pages/returns">Returns & Refunds</a> page.</p>
<h2>7. Warranty</h2>
<p>Products are covered by the legal conformity guarantee (24 months for consumers).</p>
<h2>8. Governing law</h2>
<p>Italian law applies. Jurisdiction: [PLACEHOLDER — registered city].</p>""",
    },
}
