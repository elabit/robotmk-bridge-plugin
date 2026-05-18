"""OWASP ZAP XML test data generator."""

import random
from datetime import datetime
from pathlib import Path
from typing import Dict


def generate(
    output_path: Path,
    test_status: str = "passed",
    handler_def: Dict = None,
    num_sites: int = 3,
    **kwargs
) -> None:
    """Generate an OWASP ZAP XML report file matching v2.7.0 format.
    
    ZAP reports contain alerts with risk levels (0=Info, 1=Low, 2=Medium, 3=High)
    and confidence levels (0=Low, 1=Medium, 2=High, 3=Confirmed).
    
    Args:
        output_path: Path where the XML file should be written
        test_status: 'passed' (low risk only), 'failed' (high risk), 'mixed' (varied)
        handler_def: Handler definition from handlers.yaml (unused here)
        num_sites: Number of sites to include in report
        **kwargs: Additional parameters (ignored)
    """
    # Generate timestamp in ZAP format: "Tue, 7 Aug 2018 13:17:56"
    now = datetime.now()
    timestamp = now.strftime("%a, %-d %b %Y %H:%M:%S")
    
    lines = ['<?xml version="1.0"?>']
    lines.append(f'<OWASPZAPReport version="2.7.0" generated="{timestamp}">')
    
    # Define sites to scan with varied number
    sites = [
        {"name": "http://localhost:7272", "host": "localhost", "port": "7272", "ssl": "false"},
        {"name": "http://127.0.0.1:7272", "host": "127.0.0.1", "port": "7272", "ssl": "false"},
        {"name": "http://192.168.50.56:7272", "host": "192.168.50.56", "port": "7272", "ssl": "false"},
    ][:num_sites]
    
    # Get all available alert types - only use low risk (passing tests)
    low_alerts = get_low_risk_alerts()
    
    # Generate sites with alerts (only low-risk = all passing)
    for site_idx, site_config in enumerate(sites):
        lines.append(f'<site name="{site_config["name"]}" host="{site_config["host"]}" '
                    f'port="{site_config["port"]}" ssl="{site_config["ssl"]}">')
        lines.append('<alerts>')
        
        # Randomize number of alerts per site (vary runtime simulation)
        num_alerts = random.randint(2, 6)
        site_alerts = []
        
        for _ in range(num_alerts):
            # Only choose low risk alerts (all tests pass)
            alert = random.choice(low_alerts).copy()
            
            # Vary the number of instances (affects processing time)
            alert["max_instances"] = random.randint(1, 8)
            site_alerts.append(alert)
        
        for alert in site_alerts:
            lines.extend(generate_alert_xml(alert, site_config, site_idx))
        
        lines.append('</alerts>')
        lines.append('</site>')
    
    lines.append('</OWASPZAPReport>\n')
    
    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("".join(lines))


def generate_alert_xml(alert_template: Dict, site_config: Dict, site_idx: int):
    """Generate XML lines for a single alert item."""
    lines = ['<alertitem>\n']
    
    # Core alert info
    lines.append(f'  <pluginid>{alert_template["pluginid"]}</pluginid>\n')
    lines.append(f'  <alert>{alert_template["name"]}</alert>\n')
    lines.append(f'  <name>{alert_template["name"]}</name>\n')
    lines.append(f'  <riskcode>{alert_template["riskcode"]}</riskcode>\n')
    lines.append(f'  <confidence>{alert_template["confidence"]}</confidence>\n')
    lines.append(f'  <riskdesc>{alert_template["riskdesc"]}</riskdesc>\n')
    lines.append(f'  <desc>{alert_template["desc"]}</desc>\n')
    
    # Instances - vary count to simulate different scan complexities/runtimes
    lines.append('  <instances>\n')
    max_instances = alert_template.get("max_instances", 3)
    num_instances = random.randint(1, max_instances)
    
    for i in range(num_instances):
        lines.append('  <instance>\n')
        
        # Generate URI variations
        base_url = site_config["name"]
        paths = alert_template.get("paths", ["/", "/index.html", "/api/data"])
        uri = f'{base_url}{random.choice(paths)}'
        lines.append(f'  <uri>{uri}</uri>\n')
        
        method = random.choice(["GET", "POST"])
        lines.append(f'  <method>{method}</method>\n')
        
        lines.append(f'  <param>{alert_template["param"]}</param>\n')
        
        if "evidence" in alert_template:
            lines.append(f'  <evidence>{alert_template["evidence"]}</evidence>\n')
        
        lines.append('  </instance>\n')
    
    lines.append('  </instances>\n')
    lines.append(f'  <count>{num_instances}</count>\n')
    
    # Solutions and references
    lines.append(f'  <solution>{alert_template["solution"]}</solution>\n')
    
    if "otherinfo" in alert_template:
        lines.append(f'  <otherinfo>{alert_template["otherinfo"]}</otherinfo>\n')
    
    lines.append(f'  <reference>{alert_template["reference"]}</reference>\n')
    lines.append(f'  <cweid>{alert_template["cweid"]}</cweid>\n')
    lines.append(f'  <wascid>{alert_template["wascid"]}</wascid>\n')
    lines.append(f'  <sourceid>3</sourceid>\n')
    lines.append('</alertitem>\n')
    
    return lines


def get_low_risk_alerts():
    """Return low-risk security alerts."""
    return [
        {
            "pluginid": "10021",
            "name": "X-Content-Type-Options Header Missing",
            "riskcode": "1",
            "confidence": "2",
            "riskdesc": "Low (Medium)",
            "desc": "&lt;p&gt;The Anti-MIME-Sniffing header X-Content-Type-Options was not set to &apos;nosniff&apos;. This allows older versions of Internet Explorer and Chrome to perform MIME-sniffing on the response body, potentially causing the response body to be interpreted and displayed as a content type other than the declared content type. Current (early 2014) and legacy versions of Firefox will use the declared content type (if one is set), rather than performing MIME-sniffing.&lt;/p&gt;",
            "param": "X-Content-Type-Options",
            "max_instances": 5,
            "paths": ["/", "/demo.css", "/welcome.html", "/error.html"],
            "solution": "&lt;p&gt;Ensure that the application/web server sets the Content-Type header appropriately, and that it sets the X-Content-Type-Options header to &apos;nosniff&apos; for all web pages.&lt;/p&gt;&lt;p&gt;If possible, ensure that the end user uses a standards-compliant and modern web browser that does not perform MIME-sniffing at all, or that can be directed by the web application/web server to not perform MIME-sniffing.&lt;/p&gt;",
            "otherinfo": "&lt;p&gt;This issue still applies to error type pages (401, 403, 500, etc) as those pages are often still affected by injection issues, in which case there is still concern for browsers sniffing pages away from their actual content type.&lt;/p&gt;&lt;p&gt;At &quot;High&quot; threshold this scanner will not alert on client or server error responses.&lt;/p&gt;",
            "reference": "&lt;p&gt;http://msdn.microsoft.com/en-us/library/ie/gg622941%28v=vs.85%29.aspx&lt;/p&gt;&lt;p&gt;https://www.owasp.org/index.php/List_of_useful_HTTP_headers&lt;/p&gt;",
            "cweid": "16",
            "wascid": "15",
        },
        {
            "pluginid": "10016",
            "name": "Web Browser XSS Protection Not Enabled",
            "riskcode": "1",
            "confidence": "2",
            "riskdesc": "Low (Medium)",
            "desc": "&lt;p&gt;Web Browser XSS Protection is not enabled, or is disabled by the configuration of the &apos;X-XSS-Protection&apos; HTTP response header on the web server&lt;/p&gt;",
            "param": "X-XSS-Protection",
            "max_instances": 7,
            "paths": ["/", "/welcome.html", "/error.html", "/favicon.ico", "/robots.txt", "/sitemap.xml"],
            "solution": "&lt;p&gt;Ensure that the web browser&apos;s XSS filter is enabled, by setting the X-XSS-Protection HTTP response header to &apos;1&apos;.&lt;/p&gt;",
            "otherinfo": "&lt;p&gt;The X-XSS-Protection HTTP response header allows the web server to enable or disable the web browser&apos;s XSS protection mechanism. The following values would attempt to enable it: &lt;/p&gt;&lt;p&gt;X-XSS-Protection: 1; mode=block&lt;/p&gt;&lt;p&gt;X-XSS-Protection: 1; report=http://www.example.com/xss&lt;/p&gt;&lt;p&gt;The following values would disable it:&lt;/p&gt;&lt;p&gt;X-XSS-Protection: 0&lt;/p&gt;&lt;p&gt;The X-XSS-Protection HTTP response header is currently supported on Internet Explorer, Chrome and Safari (WebKit).&lt;/p&gt;&lt;p&gt;Note that this alert is only raised if the response body could potentially contain an XSS payload (with a text-based content type, with a non-zero length).&lt;/p&gt;",
            "reference": "&lt;p&gt;https://www.owasp.org/index.php/XSS_(Cross_Site_Scripting)_Prevention_Cheat_Sheet&lt;/p&gt;&lt;p&gt;https://blog.veracode.com/2014/03/guidelines-for-setting-security-headers/&lt;/p&gt;",
            "cweid": "933",
            "wascid": "14",
        },
        {
            "pluginid": "10012",
            "name": "Password Autocomplete in Browser",
            "riskcode": "1",
            "confidence": "2",
            "riskdesc": "Low (Medium)",
            "desc": "&lt;p&gt;The AUTOCOMPLETE attribute is not disabled on an HTML FORM/INPUT element containing password type input.  Passwords may be stored in browsers and retrieved.&lt;/p&gt;",
            "param": "password_field",
            "max_instances": 2,
            "paths": ["/", "/login"],
            "evidence": "&lt;input id=&quot;password_field&quot; size=&quot;30&quot; type=&quot;password&quot;&gt;",
            "solution": "&lt;p&gt;Turn off the AUTOCOMPLETE attribute in forms or individual input elements containing password inputs by using AUTOCOMPLETE=&apos;OFF&apos;.&lt;/p&gt;",
            "reference": "&lt;p&gt;http://www.w3schools.com/tags/att_input_autocomplete.asp&lt;/p&gt;&lt;p&gt;https://msdn.microsoft.com/en-us/library/ms533486%28v=vs.85%29.aspx&lt;/p&gt;",
            "cweid": "525",
            "wascid": "15",
        },
    ]


def get_high_risk_alerts():
    """Return high-risk security alerts."""
    return [
        {
            "pluginid": "40018",
            "name": "SQL Injection",
            "riskcode": "3",
            "confidence": "3",
            "riskdesc": "High (High)",
            "desc": "&lt;p&gt;SQL injection may be possible.&lt;/p&gt;",
            "param": "id",
            "max_instances": 3,
            "paths": ["/api/users", "/search", "/products"],
            "evidence": "You have an error in your SQL syntax",
            "solution": "&lt;p&gt;Use prepared statements and parameterized queries.&lt;/p&gt;",
            "reference": "&lt;p&gt;https://www.owasp.org/index.php/SQL_Injection&lt;/p&gt;",
            "cweid": "89",
            "wascid": "19",
        },
        {
            "pluginid": "40012",
            "name": "Cross Site Scripting (Reflected)",
            "riskcode": "3",
            "confidence": "2",
            "riskdesc": "High (Medium)",
            "desc": "&lt;p&gt;Cross-site Scripting (XSS) is possible.&lt;/p&gt;",
            "param": "query",
            "max_instances": 2,
            "paths": ["/search", "/comment"],
            "evidence": "&lt;script&gt;alert(1)&lt;/script&gt;",
            "solution": "&lt;p&gt;Validate all input and encode all output.&lt;/p&gt;",
            "reference": "&lt;p&gt;https://www.owasp.org/index.php/XSS&lt;/p&gt;",
            "cweid": "79",
            "wascid": "8",
        },
        {
            "pluginid": "10020",
            "name": "X-Frame-Options Header Not Set",
            "riskcode": "2",
            "confidence": "2",
            "riskdesc": "Medium (Medium)",
            "desc": "&lt;p&gt;X-Frame-Options header is not included in the HTTP response to protect against &apos;ClickJacking&apos; attacks.&lt;/p&gt;",
            "param": "X-Frame-Options",
            "max_instances": 4,
            "paths": ["/", "/welcome.html", "/error.html"],
            "solution": "&lt;p&gt;Most modern Web browsers support the X-Frame-Options HTTP header. Ensure it&apos;s set on all web pages returned by your site (if you expect the page to be framed only by pages on your server (e.g. it&apos;s part of a FRAMESET) then you&apos;ll want to use SAMEORIGIN, otherwise if you never expect the page to be framed, you should use DENY. ALLOW-FROM allows specific websites to frame the web page in supported web browsers).&lt;/p&gt;",
            "reference": "&lt;p&gt;http://blogs.msdn.com/b/ieinternals/archive/2010/03/30/combating-clickjacking-with-x-frame-options.aspx&lt;/p&gt;",
            "cweid": "16",
            "wascid": "15",
        },
    ]


def get_mixed_risk_alerts():
    """Return mix of risk levels."""
    return get_low_risk_alerts() + [
        {
            "pluginid": "10020",
            "name": "X-Frame-Options Header Not Set",
            "riskcode": "2",
            "confidence": "2",
            "riskdesc": "Medium (Medium)",
            "desc": "&lt;p&gt;X-Frame-Options header is not included in the HTTP response to protect against &apos;ClickJacking&apos; attacks.&lt;/p&gt;",
            "param": "X-Frame-Options",
            "max_instances": 4,
            "paths": ["/", "/welcome.html", "/error.html"],
            "solution": "&lt;p&gt;Most modern Web browsers support the X-Frame-Options HTTP header. Ensure it&apos;s set on all web pages returned by your site (if you expect the page to be framed only by pages on your server (e.g. it&apos;s part of a FRAMESET) then you&apos;ll want to use SAMEORIGIN, otherwise if you never expect the page to be framed, you should use DENY. ALLOW-FROM allows specific websites to frame the web page in supported web browsers).&lt;/p&gt;",
            "reference": "&lt;p&gt;http://blogs.msdn.com/b/ieinternals/archive/2010/03/30/combating-clickjacking-with-x-frame-options.aspx&lt;/p&gt;",
            "cweid": "16",
            "wascid": "15",
        },
    ]
