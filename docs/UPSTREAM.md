# Upstream Tools & Attribution

ForensicX integrates with 161 open-source forensic tools across 17 categories.
Tools are fetched from their upstream repositories by `scripts/install_tools.sh` and are never bundled into this repository.
Each tool retains its original license and attribution.

**Use only on devices and evidence you are authorized to examine.**

---

## Mobile Forensics — Android

| Tool | Author | License | Repository |
|------|--------|---------|------------|
| ALEX | Christian Peter (prosch88) | GPL-3.0 | https://github.com/prosch88/ALEX |
| ALEAPP | Alexis Brignoni | MIT | https://github.com/abrignoni/ALEAPP |
| android_triage | Mattia Epifani / Giovanni Rattaro | GPL-3.0 | https://github.com/RealityNet/android_triage |
| MVT | Amnesty International Security Lab | MVT License 1.1 | https://github.com/mvt-project/mvt |
| Andriller | Den Yakovlev | MIT | https://github.com/den4uk/andriller |
| VLEAPP | Alexis Brignoni | MIT | https://github.com/abrignoni/VLEAPP |
| AEX/MEAT | Josh Farley | MIT | https://github.com/jfarley248/MEAT |
| apktool | Connor Tumbleson | Apache-2.0 | https://apktool.org |
| jadx | Skylot | Apache-2.0 | https://github.com/skylot/jadx |
| dex2jar | Panxiaobo | Apache-2.0 | https://github.com/pxb1988/dex2jar |

## Mobile Forensics — iOS / Apple

| Tool | Author | License | Repository |
|------|--------|---------|------------|
| UFADE | Christian Peter (prosch88) | GPL-3.0 | https://github.com/prosch88/UFADE |
| iLEAPP | Alexis Brignoni | MIT | https://github.com/abrignoni/iLEAPP |
| RLEAPP | Alexis Brignoni | MIT | https://github.com/abrignoni/RLEAPP |
| libimobiledevice | libimobiledevice contributors | LGPL-2.1 | https://libimobiledevice.org |
| iphone_backup_decrypt | James Sharkey | MIT | https://github.com/jsharkey13/iphone_backup_decrypt |

## Disk & Image Forensics

| Tool | Author | License | Repository |
|------|--------|---------|------------|
| Autopsy | Sleuth Kit Labs | Apache-2.0 | https://www.autopsy.com |
| The Sleuth Kit | Brian Carrier | IBM/CPL/GPL | https://www.sleuthkit.org |
| FTK Imager | AccessData / Exterro | Proprietary freeware | https://www.exterro.com/ftk-imager |
| bulk_extractor | Simson Garfinkel | Public Domain | https://github.com/simsong/bulk_extractor |
| Scalpel | Golden Richard / Vassil Roussev | GPL-2.0 | https://github.com/sleuthkit/scalpel |
| foremost | Jesse Kornblum / Kris Kendall | Public Domain | http://foremost.sourceforge.net |
| PhotoRec / TestDisk | Christophe Grenier | GPL-2.0 | https://www.cgsecurity.org |
| dc3dd | DoD Cyber Crime Center | GPL-3.0 | https://sourceforge.net/projects/dc3dd/ |
| ewf-tools | Joachim Metz | LGPL-3.0 | https://github.com/libyal/libewf |
| xmount | Gillen Daniel | GPL-3.0 | https://www.pinguin.lu |
| afflib-tools | Simson Garfinkel | BSD | https://github.com/sshock/AFFLIBv3 |
| ddrescue | Antonio Diaz | GPL-2.0 | https://www.gnu.org/software/ddrescue/ |
| guymager | Guy Voncken | GPL-2.0 | https://guymager.sourceforge.io |
| hashdeep / ssdeep | Jesse Kornblum | PD / GPL | https://github.com/jessek/hashdeep |
| dcfldd | DoD / Nicholas Harbour | GPL-2.0 | https://sourceforge.net/projects/dcfldd/ |
| Dissect | Fox-IT | Apache-2.0 | https://github.com/fox-it/dissect |

## Memory Forensics

| Tool | Author | License | Repository |
|------|--------|---------|------------|
| Volatility 3 | Volatility Foundation | VSL 1.0 | https://github.com/volatilityfoundation/volatility3 |
| Volatility 2 | Volatility Foundation | GPL-2.0 | https://github.com/volatilityfoundation/volatility |
| LiME | Joe Sylve | GPL-2.0 | https://github.com/504ensicsLabs/LiME |
| AVML | Microsoft | MIT | https://github.com/microsoft/avml |
| MemProcFS | Ulf Frisk | AGPL-3.0 | https://github.com/ufrisk/MemProcFS |

## Log & Timeline Analysis

| Tool | Author | License | Repository |
|------|--------|---------|------------|
| Plaso (log2timeline) | Kristinn Gudjonsson | Apache-2.0 | https://github.com/log2timeline/plaso |
| Timesketch | Google | Apache-2.0 | https://timesketch.org |
| Chainsaw | WithSecure Labs | GPL-3.0 | https://github.com/WithSecureLabs/chainsaw |
| Hayabusa | Yamato Security | AGPL-3.0 | https://github.com/Yamato-Security/hayabusa |
| Sigma | Florian Roth / Thomas Patzke | LGPL-2.1 | https://github.com/SigmaHQ/sigma |
| evtx | Omer Ben-Amram | MIT | https://github.com/omerbenamram/evtx |
| LogonTracer | JPCERT/CC | MIT | https://github.com/JPCERTCC/LogonTracer |
| UAC | Thiago Canovas | Apache-2.0 | https://github.com/tclahr/uac |

## Network Forensics

| Tool | Author | License | Repository |
|------|--------|---------|------------|
| Wireshark / tshark | Gerald Combs | GPL-2.0 | https://www.wireshark.org |
| NetworkMiner | Erik Hjelmvik / Netresec | GPL-2.0 | https://www.netresec.com |
| Xplico | Gianluca Costa | GPL-2.0 | https://www.xplico.org |
| Zeek | The Zeek Project | BSD | https://zeek.org |
| tcpdump | Van Jacobson | BSD | https://www.tcpdump.org |
| tcpflow | Simson Garfinkel | GPL-3.0 | https://github.com/simsong/tcpflow |
| ngrep | Jordan Ritter | BSD | https://github.com/jpr5/ngrep |
| Suricata | OISF | GPL-2.0 | https://suricata.io |
| Snort | Cisco Talos | GPL-2.0 | https://www.snort.org |
| Arkime (Moloch) | AOL/Yahoo/Verizon | Apache-2.0 | https://arkime.com |
| Kismet | Mike Kershaw (dragorn) | GPL-2.0 | https://www.kismetwireless.net |
| nfdump / nfsen | Peter Haag | BSD | https://github.com/phaag/nfdump |
| Zeek (Bro) | The Zeek Project | BSD | https://zeek.org |
| dnscat2 | Ron Bowes (iagox86) | GPL-2.0 | https://github.com/iagox86/dnscat2 |

## Artifact & File Analysis

| Tool | Author | License | Repository |
|------|--------|---------|------------|
| ExifTool | Phil Harvey | Perl Artistic | https://exiftool.org |
| RegRipper | H. Carvey | GPL-2.0 | https://github.com/keydet89/RegRipper3.0 |
| Hindsight | Ryan Benson | Apache-2.0 | https://github.com/obsidianforensics/hindsight |
| pdfid / pdf-parser | Didier Stevens | Public Domain | https://github.com/DidierStevens/DidierStevensSuite |
| oletools | Philippe Lagadec | BSD | https://github.com/decalage2/oletools |
| peepdf | Jose Miguel Esparza | GPL-2.0 | https://github.com/jesparza/peepdf |
| binwalk | Craig Heffner | MIT | https://github.com/ReFirmLabs/binwalk |
| FLOSS | Mandiant FLARE | Apache-2.0 | https://github.com/mandiant/flare-floss |
| zsteg | Zed-0xff | MIT | https://github.com/zed-0xff/zsteg |
| StegExpose | b3dk7 | MIT | https://github.com/b3dk7/StegExpose |
| steghide | Stefan Hetzl | GPL-2.0 | https://steghide.sourceforge.net |
| DFIR ORC | ANSSI | LGPL-2.1 | https://github.com/dfir-orc/dfir-orc |
| Dissect | Fox-IT | Apache-2.0 | https://github.com/fox-it/dissect |

## Password & Hash Analysis

| Tool | Author | License | Repository |
|------|--------|---------|------------|
| Hashcat | Jens Steube | MIT | https://hashcat.net |
| John the Ripper | Solar Designer | GPL-2.0 | https://www.openwall.com/john/ |
| hashID | psypanda | GPL-3.0 | https://github.com/psypanda/hashID |
| fcrackzip | Marc Lehmann | GPL-2.0 | http://oldhome.schmorp.de/marc/fcrackzip.html |
| pdfcrack | Henrik Stokseth | GPL-2.0 | https://sourceforge.net/projects/pdfcrack/ |

## Malware Analysis & Reverse Engineering

| Tool | Author | License | Repository |
|------|--------|---------|------------|
| Ghidra | NSA Research Directorate | Apache-2.0 | https://ghidra-sre.org |
| Radare2 | pancake / community | LGPL-3.0 | https://www.radare.org |
| Cutter | Rizin org | GPL-3.0 | https://cutter.re |
| YARA | Victor M. Alvarez / VirusTotal | BSD-3-Clause | https://virustotal.github.io/yara/ |
| ClamAV | Cisco Talos | GPL-2.0 | https://www.clamav.net |
| FLOSS | Mandiant FLARE | Apache-2.0 | https://github.com/mandiant/flare-floss |
| capa | Mandiant FLARE | Apache-2.0 | https://github.com/mandiant/capa |
| speakeasy | Mandiant | MIT | https://github.com/mandiant/speakeasy |
| Detect It Easy | horsicq | MIT | https://github.com/horsicq/Detect-It-Easy |
| pefile | Ero Carrera | MIT | https://github.com/erocarrera/pefile |
| MobSF | Ajin Abraham | GPL-3.0 | https://github.com/MobSF/Mobile-Security-Framework-MobSF |
| androguard | Desnos / Hugo Barre | Apache-2.0 | https://github.com/androguard/androguard |
| frida | Ole André V. Ravnås | wxWindows Library Licence | https://frida.re |
| objection | Dominic Chell (sensepost) | Apache-2.0 | https://github.com/sensepost/objection |
| Cuckoo Sandbox | Cuckoo Foundation | GPL-3.0 | https://cuckoosandbox.org |

## Incident Response

| Tool | Author | License | Repository |
|------|--------|---------|------------|
| Velociraptor | Velocidex Enterprises | AGPL-3.0 | https://www.velocidex.com |
| osquery | Meta | Apache-2.0 | https://osquery.io |
| GRR | Google | Apache-2.0 | https://github.com/google/grr |
| FastIR | SekoiaLab | GPL-3.0 | https://github.com/SekoiaLab/Fastir_Collector |
| ir-rescue | Diogo Fernan | MIT | https://github.com/diogo-fernan/ir-rescue |
| CrowdStrike Forensics | CrowdStrike | MIT | https://github.com/CrowdStrike/forensics |
| KAPE | Kroll / Eric Zimmermann | Proprietary freeware | https://www.kroll.com/kape |
| Loki | Neo23x0 (Florian Roth) | GPL-3.0 | https://github.com/Neo23x0/Loki |
| PowerForensics | Invoke-IR | Apache-2.0 | https://github.com/Invoke-IR/PowerForensics |

## Case Management & DFIR Platforms

| Tool | Author | License | Repository |
|------|--------|---------|------------|
| DFIR-IRIS | DFIR-IRIS Project | LGPL-3.0 | https://github.com/dfir-iris/iris-web |
| TheHive | StrangeBee | AGPL-3.0 | https://thehive-project.org |
| Cortex | StrangeBee | AGPL-3.0 | https://github.com/TheHive-Project/Cortex |
| OpenCTI | Filigran | Apache-2.0 | https://opencti.io |
| MISP | CIRCL | AGPL-3.0 | https://www.misp-project.org |
| Autopsy | Sleuth Kit Labs | Apache-2.0 | https://www.autopsy.com |
| Magnet AXIOM | Magnet Forensics | Commercial | https://www.magnetforensics.com |

## Windows Artifact Analysis

| Tool | Author | License | Repository |
|------|--------|---------|------------|
| LECmd | Eric Zimmermann | MIT | https://ericzimmerman.github.io |
| PECmd | Eric Zimmermann | MIT | https://ericzimmerman.github.io |
| JLECmd | Eric Zimmermann | MIT | https://ericzimmerman.github.io |
| MFTCmd | Eric Zimmermann | MIT | https://ericzimmerman.github.io |
| RBCmd | Eric Zimmermann | MIT | https://ericzimmerman.github.io |
| AppCompatCacheParser | Eric Zimmermann | MIT | https://ericzimmerman.github.io |
| AmcacheParser | Eric Zimmermann | MIT | https://ericzimmerman.github.io |
| EvtxECmd | Eric Zimmermann | MIT | https://ericzimmerman.github.io |
| SrumECmd | Eric Zimmermann | MIT | https://ericzimmerman.github.io |
| WxTCmd | Eric Zimmermann | MIT | https://ericzimmerman.github.io |
| ShimCacheParser | Mandiant | Apache-2.0 | https://github.com/mandiant/ShimCacheParser |
| Registry Explorer | Eric Zimmermann | MIT | https://ericzimmerman.github.io |

## OSINT

| Tool | Author | License | Repository |
|------|--------|---------|------------|
| SpiderFoot | Steve Micallef | MIT | https://www.spiderfoot.net |
| theHarvester | Christian Martorella | GPL-2.0 | https://github.com/laramies/theHarvester |
| Sherlock | Sherlock Project | MIT | https://github.com/sherlock-project/sherlock |
| Recon-ng | Tim Tomes | GPL-3.0 | https://github.com/lanmaster53/recon-ng |
| Photon | s0md3v | GPL-3.0 | https://github.com/s0md3v/Photon |
| Maltego Community | Paterva | Proprietary (CE free) | https://www.maltego.com |
| OSINT Framework | lockfale | MIT | https://github.com/lockfale/osint-framework |

## Cloud & Container Forensics

| Tool | Author | License | Repository |
|------|--------|---------|------------|
| docker-explorer | Google | Apache-2.0 | https://github.com/google/docker-explorer |
| aws-ir | ThreatResponse | Apache-2.0 | https://github.com/ThreatResponse/aws_ir |
| pacu | Rhino Security Labs | BSD-3-Clause | https://github.com/RhinoSecurityLabs/pacu |
| TruffleHog | Truffle Security | AGPL-3.0 | https://github.com/trufflesecurity/trufflehog |
| Grype | Anchore | Apache-2.0 | https://github.com/anchore/grype |

## Reporting & Utilities

| Tool | Author | License | Repository |
|------|--------|---------|------------|
| dfimagetools | Joachim Metz | Apache-2.0 | https://github.com/libyal/dfimagetools |
| dfvfs | log2timeline contributors | Apache-2.0 | https://github.com/log2timeline/dfvfs |
| Timeline Lab | CERT Société Générale | MIT | https://github.com/certsocietegenerale/timeline-lab |

## Forensic Distros (Reference)

| Distribution | Maintainer | License | Website |
|--------------|------------|---------|---------|
| SIFT Workstation | SANS Institute | Freeware | https://www.sans.org/tools/sift-workstation/ |
| CAINE | Nanni Bassetti | GPL/Various | https://www.caine-live.net |
| PALADIN | SUMURI | Proprietary (free) | https://sumuri.com/software/paladin/ |
| Tsurugi Linux | Tsurugi Team | GPL/Various | https://tsurugi-linux.org |

## Commercial Tools (Reference Only)

These tools are documented for reference. ForensicX does not install, bundle, or replicate them.
The hub shows their homepage when selected.

| Tool | Vendor | Category |
|------|--------|----------|
| Cellebrite UFED | Cellebrite | Mobile acquisition |
| Magnet AXIOM | Magnet Forensics | All-in-one forensics |
| EnCase Forensic | OpenText | Disk & enterprise |
| X-Ways Forensics | X-Ways | Disk & file forensics |
| Belkasoft Evidence Center | Belkasoft | All-in-one forensics |
| Oxygen Forensic Detective | Oxygen Forensics | Mobile forensics |
| FTK (Forensic Toolkit) | AccessData / Exterro | Disk & enterprise |
| Nuix Workstation | Nuix | eDiscovery & forensics |
| Cyber Triage | Sleuth Kit Labs | Automated IR triage |

---

All tools remain under their own licenses.
ForensicX hub code is Apache-2.0.
**Use only on devices and evidence you are authorized to examine.**
