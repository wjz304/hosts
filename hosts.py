import argparse
import json
import os
import platform
import subprocess
import sys
import time
from typing import Optional

# Auto-install missing dependencies on first run
try:
    import requests
    from requests.adapters import HTTPAdapter
except ModuleNotFoundError:
    print("[INFO] Installing missing dependency: requests")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--quiet", "requests"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    import requests
    from requests.adapters import HTTPAdapter


def _is_admin() -> bool:
    """Check if current process has administrator privileges."""
    if platform.system() != "Windows":
        return True
    try:
        import ctypes

        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def _ensure_write_permission(file_path: str) -> None:
    """Auto-elevate to admin if writing to system hosts file."""
    if not file_path or file_path == "system":
        return
    system_hosts = SYSTEM_HOSTS.get(platform.system(), "")
    if system_hosts and os.path.abspath(file_path) == os.path.abspath(system_hosts):
        if not _is_admin():
            print("[INFO] Requesting administrator privileges via UAC...")
            script_path = os.path.abspath(__file__)
            elevated_args = [a for a in sys.argv[1:] if a not in ("--help", "-h")]
            try:
                import ctypes

                ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "runas",
                    sys.executable,
                    f'"{script_path}" {" ".join(elevated_args)}',
                    None,
                    1,
                )
            except Exception as e:
                print(f"[ERROR] Failed to elevate: {e}", file=sys.stderr)
                sys.exit(1)
            sys.exit(0)


# Path for domain groups persistence (JSON alongside this script)
DOMAINS_FILE: str = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "domains.json"
)

# Default domain groups (fallback when no JSON file exists)
DEFAULT_DOMAIN_GROUPS: dict[str, list[str]] = {
    "GitHub": [
        "github.io",
        "github.com",
        "github.blog",
        "github.community",
        "api.github.com",
        "api.githubcopilot.com",
        "gist.github.com",
        "codeload.github.com",
        "central.github.com",
        "collector.github.com",
        "raw.github.com",
        "docs.github.com",
        "assets-cdn.github.com",
        "raw.githubusercontent.com",
        "camo.githubusercontent.com",
        "cloud.githubusercontent.com",
        "media.githubusercontent.com",
        "desktop.githubusercontent.com",
        "objects.githubusercontent.com",
        "favicons.githubusercontent.com",
        "avatars5.githubusercontent.com",
        "avatars4.githubusercontent.com",
        "avatars3.githubusercontent.com",
        "avatars2.githubusercontent.com",
        "avatars1.githubusercontent.com",
        "avatars0.githubusercontent.com",
        "avatars.githubusercontent.com",
        "user-images.githubusercontent.com",
        "copilot-proxy.githubusercontent.com",
        "release-assets.githubusercontent.com",
        "github-releases.githubusercontent.com",
        "pipelines.actions.githubusercontent.com",
        "pipelinesghubeus7.actions.githubusercontent.com",
        "githubstatus.com",
        "collector.githubapp.com",
        "github.githubassets.com",
        "analytics.githubassets.com",
        "github.map.fastly.net",
        "github.global.ssl.fastly.net",
        "github-cloud.s3.amazonaws.com",
        "github-com.s3.amazonaws.com",
        "github-production-release-asset-2e65be.s3.amazonaws.com",
        "github-production-user-asset-6210df.s3.amazonaws.com",
        "github-production-repository-file-5c1aeb.s3.amazonaws.com",
    ],
    "Docker": [
        "hub.docker.com",
        "registry.hub.docker.com",
        "index.docker.io",
        "ghcr.io",
        "gcr.io",
        "k8s.gcr.io",
        "quay.io",
    ],
    "TMM": [
        "themoviedb.org",
        "www.themoviedb.org",
        "api.themoviedb.org",
        "tmdb.org",
        "api.tmdb.org",
        "image.tmdb.org",
        "opensubtitles.org",
        "www.opensubtitles.org",
        "api.opensubtitles.org",
        "assets.fanart.tv",
    ],
    "DSM": [
        "www.synology.com",
        "find.synology.com",
        "account.synology.com",
        "kb.synology.com",
        "help.synology.com",
        "router.synology.com",
        "notification.synology.com",
        "sns.synology.com",
        "www-ai.synology.com",
        "archive.synology.com",
        "update7.synology.com",
        "pkgupdate7.synology.com",
        "global.download.synology.com",
        "webec.synology.com",
        "fileres.synology.com",
        "gallery.synology.com",
        "synostatic.synology.com",
        "www.synology.cn",
        "find.synology.cn",
        "account.synology.cn",
        "kb.synology.cn",
        "archive.synology.cn",
        "cndl.synology.cn",
        "global.synologydownload.com",
    ],
}


DNS_SERVERS: dict[str, tuple[str, dict]] = {
    "Cloudflare": (
        "https://cloudflare-dns.com/dns-query?name={}&type={}",
        {"accept": "application/dns-json"},
    ),
    "Google": ("https://dns.google/resolve?name={}&type={}", {}),
    "Aliyun": ("https://dns.alidns.com/resolve?name={}&type={}", {}),
}

# DNS record type mapping: name -> numeric type code
DNS_TYPES: dict[str, int] = {
    "A": 1,
    "AAAA": 28,
}

# System hosts file paths by OS
SYSTEM_HOSTS: dict[str, str] = {
    "Windows": r"C:\Windows\System32\drivers\etc\hosts",
    "Linux": "/etc/hosts",
    "Darwin": "/etc/hosts",
}


class DNSChecker:
    """DNS resolver for checking domain records."""

    def __init__(self, provider: str = "Cloudflare") -> None:
        self.provider = provider if provider in DNS_SERVERS else "Cloudflare"
        self._session = self._create_session()

    @staticmethod
    def _create_session() -> requests.Session:
        """Create a session with timeout control to prevent hanging."""
        session = requests.Session()
        adapter = HTTPAdapter(
            max_retries=0,
            pool_connections=10,
            pool_maxsize=10,
            pool_block=False,
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _query(self, qname: str, rdtype: str = "A") -> Optional[dict]:
        """Query DNS server for the given record type."""
        server = DNS_SERVERS.get(self.provider)
        if not server:
            return None
        url, headers = server
        try:
            # Split timeout: (connect_timeout, read_timeout) to avoid long stalls
            resp = self._session.get(
                url.format(qname, rdtype),
                headers=headers,
                timeout=(3, 5),
            )
            if resp.status_code != 200:
                return None
            return resp.json()
        except requests.RequestException:
            return None

    def resolve(self, domain: str, rdtype: str = "A") -> Optional[str]:
        """Resolve domain to first IP of the given record type, with CNAME fallback.

        Args:
            domain: Domain name to resolve.
            rdtype: DNS record type ('A' for IPv4, 'AAAA' for IPv6).

        Returns:
            IP string, or None if resolution failed.
        """
        record_num = DNS_TYPES.get(rdtype)
        if record_num is None:
            return None

        try:
            data = self._query(domain, rdtype)
            if not data or data.get("Status") != 0:
                return None

            for ans in data.get("Answer") or []:
                if ans.get("type") == record_num and ans.get("data"):
                    return ans["data"]

            # Fallback: try CNAME resolution
            cname_data = self._query(domain, "CNAME")
            if not cname_data or cname_data.get("Status") != 0:
                return None

            for ans in cname_data.get("Answer") or []:
                if ans.get("type") == 5 and ans.get("data"):
                    target = ans["data"].rstrip(".")
                    target_data = self._query(target, rdtype)
                    if target_data and target_data.get("Status") == 0:
                        for t_ans in target_data.get("Answer") or []:
                            if t_ans.get("type") == record_num and t_ans.get("data"):
                                return t_ans["data"]
            return None
        except Exception:
            return None


def load_domain_groups() -> dict[str, list[str]]:
    """Load domain groups from JSON file, falling back to defaults."""
    if os.path.exists(DOMAINS_FILE):
        try:
            with open(DOMAINS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return {k: list(v) for k, v in data.items()}
        except (json.JSONDecodeError, OSError) as e:
            print(f"[WARNING] Failed to load {DOMAINS_FILE}: {e}", file=sys.stderr)
    return {k: list(v) for k, v in DEFAULT_DOMAIN_GROUPS.items()}


def save_domain_groups(groups: dict[str, list[str]]) -> None:
    """Save domain groups to JSON file."""
    with open(DOMAINS_FILE, "w", encoding="utf-8") as f:
        json.dump(groups, f, indent=2, ensure_ascii=False)
    print(f"[INFO] Domain groups saved to {DOMAINS_FILE}")


def list_groups(groups: dict[str, list[str]]) -> None:
    """Print all domain groups in a readable format."""
    if not groups:
        print("[INFO] No domain groups configured.")
        return
    for name, domains in groups.items():
        print(f"\n{name} ({len(domains)} domains):")
        for d in domains:
            print(f"  - {d}")


# Section markers for updating hosts file without duplicates
ING_START: str = "# ING Hosts Start"
ING_END: str = "# ING Hosts End"


def _replace_section(file_path: str, content: str = "") -> bool:
    """Replace or remove the ING Hosts section in an existing file.

    If *content* is non-empty, the section is replaced with the given content.
    If *content* is empty, the section is removed.

    The content should include the ING START/END markers.

    Returns True if the file was modified, False on error.
    """
    if not os.path.exists(file_path):
        if content == "":
            return False
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    start_idx = end_idx = None
    for i, line in enumerate(lines):
        if ING_START in line and start_idx is None:
            start_idx = i
        if ING_END in line and start_idx is not None:
            end_idx = i
            break

    if content == "":
        if start_idx is None or end_idx is None:
            return False
        new_lines = lines[:start_idx] + lines[end_idx + 1 :]
        text = "".join(new_lines).rstrip("\n") + "\n"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)
        return True

    if start_idx is not None and end_idx is not None:
        new_lines = lines[:start_idx] + [content] + lines[end_idx + 1 :]
    else:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        new_lines = lines + [content]

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    return True


def generate_hosts(
    provider: str = "Cloudflare",
    rdtype: str = "A",
    groups: Optional[dict[str, list[str]]] = None,
) -> str:
    """Generate hosts file content as a single string.

    Args:
        provider: DNS provider name (Cloudflare, Google, Aliyun).
        rdtype: DNS record type ('A' for IPv4, 'AAAA' for IPv6).
        groups: Domain groups dict. If None, loaded from JSON/defaults.
    """
    if groups is None:
        groups = load_domain_groups()
    checker = DNSChecker(provider)

    lines: list[str] = [
        "# ING Hosts Start",
        "# Raw Url: https://raw.githubusercontent.com/wjz304/hosts/main/hosts",
        "# CDN Url: https://gcore.jsdelivr.net/gh/wjz304/hosts@main/hosts",
        "# CDN Url: https://cdn.staticaly.com/gh/wjz304/hosts/main/hosts",
        f"# DNS Servers: {provider}",
        f"# Record Type: {rdtype}",
        f"# Update at: {time.strftime('%Y-%m-%d %H:%M:%S')}",
    ]

    for group_name, domains in groups.items():
        lines.append(f"# {group_name} Hosts Start")
        for domain in domains:
            ip = checker.resolve(domain, rdtype)
            if ip:
                lines.append(f"{ip.ljust(16 if rdtype == 'A' else 40)}{domain}")
        lines.append(f"# {group_name} Hosts End")

    lines.append("# ING Hosts End")
    return "\n".join(lines) + "\n"


def main() -> None:
    """Parse arguments and perform requested operations."""
    parser = argparse.ArgumentParser(
        description="Manage domain groups and generate hosts file via DNS resolution."
    )
    parser.add_argument(
        "--dns",
        default="Cloudflare",
        choices=list(DNS_SERVERS.keys()),
        help="DNS provider to use (default: Cloudflare)",
    )
    parser.add_argument(
        "--type",
        default="A",
        choices=list(DNS_TYPES.keys()),
        help="DNS record type: A (IPv4) or AAAA (IPv6) (default: A)",
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="Generate and write the ING Hosts section to the output file (default: system hosts file)",
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove the ING Hosts section from the output file (default: system hosts file)",
    )
    parser.add_argument(
        "--output",
        default="system",
        help="Output path. 'system' for OS hosts file, or a custom path (default: system)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated hosts content to stdout instead of writing to file",
    )
    # Domain group CRUD operations
    parser.add_argument(
        "--list-groups",
        action="store_true",
        help="List all domain groups with their domains",
    )
    parser.add_argument(
        "--add-group",
        help="Add a new domain group: --add-group GROUP",
    )
    parser.add_argument(
        "--del-group",
        help="Delete a domain group: --del-group GROUP",
    )
    parser.add_argument(
        "--add-domain",
        nargs="+",
        help="Add domain(s) to a group: --add-domain GROUP DOMAIN1 [DOMAIN2 ...]",
    )
    parser.add_argument(
        "--del-domain",
        nargs="+",
        help="Remove domain(s) from a group: --del-domain GROUP DOMAIN1 [DOMAIN2 ...]",
    )

    args = parser.parse_args()
    groups = load_domain_groups()

    # No arguments: show help
    if len(sys.argv) == 1:
        parser.print_help()
        return

    # --list-groups
    if args.list_groups:
        list_groups(groups)
        return

    # --add-group GROUP
    if args.add_group:
        group = args.add_group
        if group in groups:
            print(f"[ERROR] Group '{group}' already exists", file=sys.stderr)
            sys.exit(1)
        groups[group] = []
        save_domain_groups(groups)
        print(f"[INFO] Added group '{group}'")
        return

    # --del-group GROUP
    if args.del_group:
        group = args.del_group
        if group not in groups:
            print(f"[ERROR] Group '{group}' not found", file=sys.stderr)
            sys.exit(1)
        del groups[group]
        save_domain_groups(groups)
        print(f"[INFO] Deleted group '{group}'")
        return

    # --add-domain GROUP DOMAIN1 [DOMAIN2 ...]
    if args.add_domain:
        group = args.add_domain[0]
        domains = args.add_domain[1:]
        if not domains:
            print("[ERROR] --add-domain requires at least one domain", file=sys.stderr)
            sys.exit(1)
        if group not in groups:
            print(f"[ERROR] Group '{group}' not found", file=sys.stderr)
            sys.exit(1)
        added = 0
        skipped = 0
        for domain in domains:
            if domain in groups[group]:
                print(f"[WARNING] Domain '{domain}' already exists in group '{group}'", file=sys.stderr)
                skipped += 1
            else:
                groups[group].append(domain)
                added += 1
        if added > 0 or skipped > 0:
            save_domain_groups(groups)
        print(
            f"[INFO] Added {added} domain(s) to group '{group}'"
            + (f", skipped {skipped} duplicate(s)" if skipped else "")
        )
        return

    # --del-domain GROUP DOMAIN1 [DOMAIN2 ...]
    if args.del_domain:
        group = args.del_domain[0]
        domains = args.del_domain[1:]
        if not domains:
            print("[ERROR] --del-domain requires at least one domain", file=sys.stderr)
            sys.exit(1)
        if group not in groups:
            print(f"[ERROR] Group '{group}' not found", file=sys.stderr)
            sys.exit(1)
        removed = 0
        skipped = 0
        for domain in domains:
            if domain not in groups[group]:
                print(
                    f"[ERROR] Domain '{domain}' not found in group '{group}'",
                    file=sys.stderr,
                )
                sys.exit(1)
            groups[group].remove(domain)
            removed += 1
        if removed > 0:
            save_domain_groups(groups)
        print(f"[INFO] Removed {removed} domain(s) from group '{group}'")
        return

    # --create: create ING Hosts section
    if args.create:
        content = generate_hosts(provider=args.dns, rdtype=args.type, groups=groups)
        output_path = (
            SYSTEM_HOSTS.get(platform.system(), "/etc/hosts")
            if args.output == "system"
            else args.output
        )
        if args.output == "system":
            _ensure_write_permission(output_path)
        if _replace_section(output_path, content=content):
            print(f"[INFO] Written ING Hosts section to {output_path}")
        else:
            print(f"[ERROR] Failed to write ING Hosts section to {output_path}")
        return

    # --remove: remove ING Hosts section
    if args.remove:
        output_path = (
            SYSTEM_HOSTS.get(platform.system(), "/etc/hosts")
            if args.output == "system"
            else args.output
        )
        if args.output == "system":
            _ensure_write_permission(output_path)
        if _replace_section(output_path, content=""):
            print(f"[INFO] Removed ING Hosts section from {output_path}")
        else:
            print(f"[WARNING] No ING Hosts section found in {output_path}")
        return

    # --dry-run: print generated hosts content
    if args.dry_run:
        content = generate_hosts(provider=args.dns, rdtype=args.type, groups=groups)
        print(content)
        return

    # No matching operation: show help
    parser.print_help()


if __name__ == "__main__":
    main()
