# Upstream Tools & Attribution

ForensicX integrates with 60+ open-source forensic tools.
Tools are fetched from their upstream repositories by `scripts/install_tools.sh` and are never bundled into this repository.
Each tool retains its original license and attribution.

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

## OSINT

| Tool | Author | License | Repository |
|------|--------|---------|------------|
| SpiderFoot | Steve Micallef | MIT | https://www.spiderfoot.net |
| theHarvester | Christian Martorella | GPL-2.0 | https://github.com/laramies/theHarvester |
| Sherlock | Sherlock Project | MIT | https://github.com/sherlock-project/sherlock |
| Recon-ng | Tim Tomes | GPL-3.0 | https://github.com/lanmaster53/recon-ng |
| Photon | s0md3v | GPL-3.0 | https://github.com/s0md3v/Photon |
| Maltego Community | Paterva | Proprietary (CE free) | https://www.maltego.com |

## Cloud & Container Forensics

| Tool | Author | License | Repository |
|------|--------|---------|------------|
| docker-explorer | Google | Apache-2.0 | https://github.com/google/docker-explorer |
| aws-ir | ThreatResponse | Apache-2.0 | https://github.com/ThreatResponse/aws_ir |
| pacu | Rhino Security Labs | BSD-3-Clause | https://github.com/RhinoSecurityLabs/pacu |
| TruffleHog | Truffle Security | AGPL-3.0 | https://github.com/trufflesecurity/trufflehog |

## Reporting & Utilities

| Tool | Author | License | Repository |
|------|--------|---------|------------|
| dfimagetools | Joachim Metz | Apache-2.0 | https://github.com/libyal/dfimagetools |
| dfvfs | log2timeline contributors | Apache-2.0 | https://github.com/log2timeline/dfvfs |
| Timeline Lab | CERT Société Générale | MIT | https://github.com/certsocietegenerale/timeline-lab |

---

All tools remain under their own licenses.
ForensicX hub code is Apache-2.0.
**Use only on devices and evidence you are authorized to examine.**
