"""联网信息增强器 - 为视频分析结果提供时效性验证和权威信息补充。

通过联网检索工具的最新版本、安装命令、文档链接等信息，
验证视频中介绍的内容是否仍然有效，并补充权威来源引用。
"""

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


@dataclass
class EnrichedTool:
    """增强后的工具信息。"""
    name: str                              # 工具名称
    latest_version: str = ""               # 最新版本号
    latest_release_date: str = ""          # 最新发布日期
    verified_install_commands: list[str] = field(default_factory=list)   # 验证后的安装命令
    official_docs_url: str = ""            # 官方文档链接
    github_url: str = ""                   # GitHub 仓库链接
    github_stars: int = 0                  # GitHub 星标数
    package_registry_url: str = ""         # 包管理源链接（PyPI/npm）
    source_references: list[dict] = field(default_factory=list)  # 信息来源引用
    warnings: list[str] = field(default_factory=list)            # 时效性警告
    video_commands_match: bool = True      # 视频中的命令与最新信息是否一致
    search_time: str = ""                  # 检索时间（ISO 格式）


@dataclass
class EnrichmentResult:
    """完整的增强结果。"""
    tools: list[EnrichedTool] = field(default_factory=list)
    enriched_at: str = ""                  # 增强时间
    total_sources_consulted: int = 0       # 查阅的源数量
    discrepancies_found: int = 0           # 发现的差异数量


# ── 注册表：常见工具的权威信息源 ──────────────────────────────────────

TOOL_REGISTRY = {
    # === Python 生态 ===
    "pip": {
        "package_registry": "https://pypi.org/project/pip/",
        "install_check": "pip --version",
    },
    "pip3": {"alias": "pip"},
    "python": {
        "official_docs": "https://docs.python.org/3/",
        "github": "https://github.com/python/cpython",
        "install_check": "python --version",
    },
    "python3": {"alias": "python"},
    "poetry": {
        "official_docs": "https://python-poetry.org/docs/",
        "github": "https://github.com/python-poetry/poetry",
        "package_registry": "https://pypi.org/project/poetry/",
        "install_check": "poetry --version",
    },
    "pipenv": {
        "official_docs": "https://pipenv.pypa.io/",
        "github": "https://github.com/pypa/pipenv",
        "package_registry": "https://pypi.org/project/pipenv/",
    },
    "conda": {
        "official_docs": "https://docs.conda.io/",
        "github": "https://github.com/conda/conda",
        "install_check": "conda --version",
    },
    "pyenv": {
        "official_docs": "https://github.com/pyenv/pyenv#readme",
        "github": "https://github.com/pyenv/pyenv",
        "install_check": "pyenv --version",
    },
    "jupyter": {
        "official_docs": "https://jupyter.org/documentation",
        "github": "https://github.com/jupyter/jupyter",
        "package_registry": "https://pypi.org/project/jupyter/",
    },
    "notebook": {"alias": "jupyter"},
    "fastapi": {
        "official_docs": "https://fastapi.tiangolo.com/",
        "github": "https://github.com/fastapi/fastapi",
        "package_registry": "https://pypi.org/project/fastapi/",
        "install_check": "pip install fastapi",
    },
    "uvicorn": {
        "official_docs": "https://www.uvicorn.org/",
        "github": "https://github.com/encode/uvicorn",
        "package_registry": "https://pypi.org/project/uvicorn/",
    },
    "pytest": {
        "official_docs": "https://docs.pytest.org/",
        "github": "https://github.com/pytest-dev/pytest",
        "package_registry": "https://pypi.org/project/pytest/",
    },
    "flask": {
        "official_docs": "https://flask.palletsprojects.com/",
        "github": "https://github.com/pallets/flask",
        "package_registry": "https://pypi.org/project/Flask/",
    },
    "django": {
        "official_docs": "https://docs.djangoproject.com/",
        "github": "https://github.com/django/django",
        "package_registry": "https://pypi.org/project/Django/",
    },
    "requests": {
        "official_docs": "https://requests.readthedocs.io/",
        "github": "https://github.com/psf/requests",
        "package_registry": "https://pypi.org/project/requests/",
    },
    "httpx": {
        "official_docs": "https://www.python-httpx.org/",
        "github": "https://github.com/encode/httpx",
        "package_registry": "https://pypi.org/project/httpx/",
    },

    # === JavaScript / Node.js 生态 ===
    "node": {
        "official_docs": "https://nodejs.org/docs/latest/api/",
        "github": "https://github.com/nodejs/node",
        "install_check": "node --version",
    },
    "nodejs": {"alias": "node"},
    "npm": {
        "official_docs": "https://docs.npmjs.com/",
        "github": "https://github.com/npm/cli",
        "package_registry": "https://www.npmjs.com/",
        "install_check": "npm --version",
    },
    "npx": {"alias": "npm"},
    "yarn": {
        "official_docs": "https://yarnpkg.com/getting-started",
        "github": "https://github.com/yarnpkg/berry",
        "install_check": "yarn --version",
    },
    "pnpm": {
        "official_docs": "https://pnpm.io/motivation",
        "github": "https://github.com/pnpm/pnpm",
        "install_check": "pnpm --version",
    },
    "typescript": {
        "official_docs": "https://www.typescriptlang.org/docs/",
        "github": "https://github.com/microsoft/TypeScript",
        "package_registry": "https://www.npmjs.com/package/typescript",
    },
    "react": {
        "official_docs": "https://react.dev/",
        "github": "https://github.com/facebook/react",
        "package_registry": "https://www.npmjs.com/package/react",
    },
    "vue": {
        "official_docs": "https://vuejs.org/guide/introduction.html",
        "github": "https://github.com/vuejs/core",
        "package_registry": "https://www.npmjs.com/package/vue",
    },
    "vite": {
        "official_docs": "https://vitejs.dev/guide/",
        "github": "https://github.com/vitejs/vite",
        "package_registry": "https://www.npmjs.com/package/vite",
    },
    "next.js": {
        "official_docs": "https://nextjs.org/docs",
        "github": "https://github.com/vercel/next.js",
        "package_registry": "https://www.npmjs.com/package/next",
    },
    "next": {"alias": "next.js"},

    # === 容器 & DevOps ===
    "docker": {
        "official_docs": "https://docs.docker.com/",
        "github": "https://github.com/docker/cli",
        "install_check": "docker --version",
    },
    "docker-compose": {
        "official_docs": "https://docs.docker.com/compose/",
        "github": "https://github.com/docker/compose",
        "install_check": "docker compose version",
    },
    "kubernetes": {
        "official_docs": "https://kubernetes.io/docs/home/",
        "github": "https://github.com/kubernetes/kubernetes",
        "install_check": "kubectl version --client",
    },
    "k8s": {"alias": "kubernetes"},
    "kubectl": {
        "official_docs": "https://kubernetes.io/docs/reference/kubectl/",
        "github": "https://github.com/kubernetes/kubectl",
    },
    "helm": {
        "official_docs": "https://helm.sh/docs/",
        "github": "https://github.com/helm/helm",
    },
    "terraform": {
        "official_docs": "https://developer.hashicorp.com/terraform/docs",
        "github": "https://github.com/hashicorp/terraform",
    },
    "ansible": {
        "official_docs": "https://docs.ansible.com/",
        "github": "https://github.com/ansible/ansible",
    },
    "nginx": {
        "official_docs": "https://nginx.org/en/docs/",
        "github": "https://github.com/nginx/nginx",
        "install_check": "nginx -v",
    },

    # === 数据库 ===
    "mysql": {
        "official_docs": "https://dev.mysql.com/doc/",
        "install_check": "mysql --version",
    },
    "postgresql": {
        "official_docs": "https://www.postgresql.org/docs/",
        "install_check": "psql --version",
    },
    "postgres": {"alias": "postgresql"},
    "redis": {
        "official_docs": "https://redis.io/docs/",
        "github": "https://github.com/redis/redis",
        "install_check": "redis-server --version",
    },
    "mongodb": {
        "official_docs": "https://www.mongodb.com/docs/",
        "github": "https://github.com/mongodb/mongo",
        "install_check": "mongod --version",
    },
    "mongo": {"alias": "mongodb"},
    "sqlite": {
        "official_docs": "https://www.sqlite.org/docs.html",
    },

    # === AI / ML ===
    "pytorch": {
        "official_docs": "https://pytorch.org/docs/stable/",
        "github": "https://github.com/pytorch/pytorch",
        "package_registry": "https://pypi.org/project/torch/",
    },
    "torch": {"alias": "pytorch"},
    "tensorflow": {
        "official_docs": "https://www.tensorflow.org/api_docs",
        "github": "https://github.com/tensorflow/tensorflow",
        "package_registry": "https://pypi.org/project/tensorflow/",
    },
    "transformers": {
        "official_docs": "https://huggingface.co/docs/transformers/index",
        "github": "https://github.com/huggingface/transformers",
        "package_registry": "https://pypi.org/project/transformers/",
    },
    "ollama": {
        "official_docs": "https://github.com/ollama/ollama#readme",
        "github": "https://github.com/ollama/ollama",
    },
    "openai": {
        "official_docs": "https://platform.openai.com/docs/",
        "package_registry": "https://pypi.org/project/openai/",
    },
    "langchain": {
        "official_docs": "https://python.langchain.com/docs/",
        "github": "https://github.com/langchain-ai/langchain",
        "package_registry": "https://pypi.org/project/langchain/",
    },
    "whisper": {
        "official_docs": "https://github.com/openai/whisper#readme",
        "github": "https://github.com/openai/whisper",
        "package_registry": "https://pypi.org/project/openai-whisper/",
    },
    "faster-whisper": {
        "github": "https://github.com/SYSTRAN/faster-whisper",
        "package_registry": "https://pypi.org/project/faster-whisper/",
    },

    # === 编辑器 & 工具 ===
    "vscode": {
        "official_docs": "https://code.visualstudio.com/docs",
        "github": "https://github.com/microsoft/vscode",
    },
    "code": {"alias": "vscode"},
    "neovim": {
        "official_docs": "https://neovim.io/doc/",
        "github": "https://github.com/neovim/neovim",
    },
    "vim": {
        "official_docs": "https://www.vim.org/docs.php",
        "github": "https://github.com/vim/vim",
    },
    "git": {
        "official_docs": "https://git-scm.com/doc",
        "github": "https://github.com/git/git",
        "install_check": "git --version",
    },
    "curl": {
        "official_docs": "https://curl.se/docs/",
        "github": "https://github.com/curl/curl",
    },
    "wget": {
        "official_docs": "https://www.gnu.org/software/wget/manual/",
        "github": "https://git.savannah.gnu.org/cgit/wget.git",
    },
    "homebrew": {
        "official_docs": "https://docs.brew.sh/",
        "github": "https://github.com/Homebrew/brew",
    },
    "brew": {"alias": "homebrew"},
    "apt": {
        "official_docs": "https://manpages.debian.org/stable/apt/apt.8.en.html",
    },
    "yum": {
        "official_docs": "https://man7.org/linux/man-pages/man8/yum.8.html",
    },
    "choco": {
        "official_docs": "https://docs.chocolatey.org/",
        "github": "https://github.com/chocolatey/choco",
    },
    "scoop": {
        "official_docs": "https://scoop.sh/#/docs",
        "github": "https://github.com/ScoopInstaller/Scoop",
    },

    # === Video-to-Action 自身 ===
    "video-to-action": {
        "github": "https://github.com/Yuan123-A11Y/video-to-action",
        "official_docs": "https://github.com/Yuan123-A11Y/video-to-action#readme",
    },
}


class WebEnricher:
    """联网信息增强器。

    核心能力：
    1. 从分析结果中提取工具名称
    2. 查询预置注册表获取权威信息源
    3. 联网检索最新版本和安装命令
    4. 验证视频内容的时效性
    5. 生成带有来源引用的增强分析结果
    """

    # ── GitHub API (未认证时限制 60 次/小时) ──
    GITHUB_API = "https://api.github.com/repos/{repo}"
    GITHUB_API_SEARCH = "https://api.github.com/search/repositories?q={query}&per_page=1"

    # ── 包管理源 API ──
    PYPI_API = "https://pypi.org/pypi/{package}/json"
    NPM_API = "https://registry.npmjs.org/{package}/latest"
    CRATES_API = "https://crates.io/api/v1/crates/{package}"
    RUBYGEMS_API = "https://rubygems.org/api/v1/gems/{package}.json"

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self._session = None
        self._github_token = self.config.get("github_token", "")

    async def _get_session(self):
        """获取或创建 httpx 会话。"""
        if self._session is None or self._session.is_closed:
            import httpx
            timeout = httpx.Timeout(15.0, connect=10.0)
            self._session = httpx.AsyncClient(timeout=timeout, follow_redirects=True)
        return self._session

    async def close(self):
        """关闭会话。"""
        if self._session and not self._session.is_closed:
            await self._session.aclose()

    # ── 公开方法 ──────────────────────────────────────────────────────

    async def enrich(self, tools: list[dict], video_platform: str = "") -> EnrichmentResult:
        """对分析结果中的工具列表进行联网增强。

        Args:
            tools: 原始工具列表（来自 LLM 分析的 JSON）
            video_platform: 视频平台名称

        Returns:
            增强后的结果
        """
        enriched_tools: list[EnrichedTool] = []
        total_sources = 0
        discrepancies = 0

        for tool in tools:
            name = tool.get("name", "")
            if not name:
                continue

            enriched = await self._enrich_single_tool(tool)
            enriched_tools.append(enriched)
            total_sources += len(enriched.source_references)
            if not enriched.video_commands_match:
                discrepancies += 1

        now = time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())
        return EnrichmentResult(
            tools=enriched_tools,
            enriched_at=now,
            total_sources_consulted=total_sources,
            discrepancies_found=discrepancies,
        )

    async def _enrich_single_tool(self, tool: dict) -> EnrichedTool:
        """增强单个工具信息。"""
        name = tool.get("name", "")
        alias = self._resolve_alias(name)
        canonical_name = alias or name

        enriched = EnrichedTool(name=name)
        registry_info = TOOL_REGISTRY.get(canonical_name.lower(), {})

        sources: list[dict] = []
        warnings: list[str] = []

        # 1. 查询 GitHub
        if registry_info.get("github"):
            github_result = await self._fetch_github_info(registry_info["github"])
            if github_result:
                enriched.github_url = registry_info["github"]
                enriched.github_stars = github_result.get("stars", 0)
                enriched.latest_version = github_result.get("latest_release", "")
                enriched.latest_release_date = github_result.get("latest_release_date", "")
                sources.append({
                    "source": "GitHub",
                    "url": registry_info["github"],
                    "info": f"⭐ {enriched.github_stars} stars, latest: {enriched.latest_version or 'N/A'}",
                    "access_time": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
                })

        # 2. 查询 PyPI
        if registry_info.get("package_registry") and "pypi.org" in registry_info["package_registry"]:
            pypi_result = await self._fetch_pypi_info(canonical_name)
            if pypi_result:
                enriched.package_registry_url = registry_info["package_registry"]
                if not enriched.latest_version:
                    enriched.latest_version = pypi_result.get("version", "")
                enriched.latest_release_date = pypi_result.get("release_date", enriched.latest_release_date)
                sources.append({
                    "source": "PyPI",
                    "url": registry_info["package_registry"],
                    "info": f"version: {pypi_result.get('version', 'N/A')}, released: {pypi_result.get('release_date', 'N/A')}",
                    "access_time": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
                })

        # 3. 查询 npm
        if registry_info.get("package_registry") and "npmjs.com" in registry_info["package_registry"]:
            npm_result = await self._fetch_npm_info(canonical_name)
            if npm_result:
                enriched.package_registry_url = registry_info["package_registry"]
                if not enriched.latest_version:
                    enriched.latest_version = npm_result.get("version", "")
                sources.append({
                    "source": "npm",
                    "url": registry_info["package_registry"],
                    "info": f"version: {npm_result.get('version', 'N/A')}",
                    "access_time": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
                })

        # 4. 设置官方文档链接
        if registry_info.get("official_docs"):
            enriched.official_docs_url = registry_info["official_docs"]
            sources.append({
                "source": "官方文档",
                "url": registry_info["official_docs"],
                "info": "权威文档来源",
                "access_time": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
            })

        # 5. 验证视频中的命令与最新信息的匹配情况
        video_commands = tool.get("install_commands", []) + tool.get("run_commands", [])
        if video_commands and enriched.latest_version:
            # 检查命令中是否包含版本号，如果包含则验证
            cmd_versions = self._extract_versions_from_commands(video_commands)
            if cmd_versions and enriched.latest_version:
                for cmd_ver in cmd_versions:
                    if cmd_ver != enriched.latest_version:
                        warnings.append(
                            f"视频中使用的版本 {cmd_ver} 与最新版本 {enriched.latest_version} 不一致"
                        )
                        enriched.video_commands_match = False

        # 6. 设备安依赖性检查
        if video_commands:
            # 检查安装命令是否需要预先安装其他工具
            for cmd in video_commands:
                prereq_warning = self._check_prerequisites(cmd)
                if prereq_warning:
                    warnings.append(prereq_warning)

        enriched.warnings = warnings
        enriched.source_references = sources
        enriched.search_time = time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime())

        return enriched

    # ── 注册表辅助 ──────────────────────────────────────────────────

    def _resolve_alias(self, name: str) -> str | None:
        """解析工具别名，返回规范名称。"""
        entry = TOOL_REGISTRY.get(name.lower(), {})
        if isinstance(entry, dict) and "alias" in entry:
            return entry["alias"]
        return None

    # ── GitHub API ────────────────────────────────────────────────────

    async def _fetch_github_info(self, repo_url: str) -> dict | None:
        """从 GitHub API 获取仓库信息。"""
        # 将 URL 转为 repo path (e.g., https://github.com/user/repo -> user/repo)
        match = re.search(r"github\.com[/:]([^/\s]+/[^/\s#?]+)", repo_url)
        if not match:
            return None
        repo_path = match.group(1).rstrip("/")

        try:
            session = await self._get_session()
            headers = {"Accept": "application/vnd.github.v3+json"}
            if self._github_token:
                headers["Authorization"] = f"token {self._github_token}"

            # 获取仓库信息
            resp = await session.get(
                self.GITHUB_API.format(repo=quote(repo_path, safe="/")),
                headers=headers,
            )
            if resp.status_code != 200:
                return None

            data = resp.json()

            # 获取最新 release
            release_url = self.GITHUB_API.format(repo=quote(repo_path, safe="/")) + "/releases/latest"
            release_resp = await session.get(release_url, headers=headers)

            result = {
                "stars": data.get("stargazers_count", 0),
                "latest_release": "",
                "latest_release_date": "",
            }

            if release_resp.status_code == 200:
                release_data = release_resp.json()
                result["latest_release"] = release_data.get("tag_name", "")
                result["latest_release_date"] = release_data.get("published_at", "")

            return result

        except Exception as e:
            logger.debug("GitHub API 查询失败 (%s): %s", repo_url, e)
            return None

    # ── PyPI API ─────────────────────────────────────────────────────

    async def _fetch_pypi_info(self, package: str) -> dict | None:
        """从 PyPI API 获取包信息。"""
        try:
            session = await self._get_session()
            resp = await session.get(self.PYPI_API.format(package=quote(package)))
            if resp.status_code != 200:
                return None

            data = resp.json()
            info = data.get("info", {})
            urls = data.get("urls", []) or []

            latest_version = info.get("version", "")
            # 从 release 信息中找最新发布时间
            release_date = ""
            if urls:
                # 取第一个上传时间作为发布时间
                for url_entry in urls:
                    upload_time = url_entry.get("upload_time_iso_8601", "")
                    if upload_time:
                        release_date = upload_time
                        break

            # 如果没有 urls，从 releases 中找
            if not release_date:
                releases = data.get("releases", {})
                if latest_version in releases:
                    release_files = releases[latest_version]
                    if release_files:
                        release_date = release_files[0].get("upload_time_iso_8601", "")

            return {
                "version": latest_version,
                "release_date": release_date,
            }

        except Exception as e:
            logger.debug("PyPI API 查询失败 (%s): %s", package, e)
            return None

    # ── npm API ──────────────────────────────────────────────────────

    async def _fetch_npm_info(self, package: str) -> dict | None:
        """从 npm registry 获取包信息。"""
        try:
            session = await self._get_session()
            resp = await session.get(self.NPM_API.format(package=quote(package)))
            if resp.status_code != 200:
                return None

            data = resp.json()
            return {
                "version": data.get("version", ""),
            }

        except Exception as e:
            logger.debug("npm API 查询失败 (%s): %s", package, e)
            return None

    # ── 辅助方法 ─────────────────────────────────────────────────────

    @staticmethod
    def _extract_versions_from_commands(commands: list[str]) -> list[str]:
        """从命令中提取版本号。"""
        versions = []
        for cmd in commands:
            # 匹配 @version, ==version, @latest 等
            matches = re.findall(r"[@=]=?\s*(\d+\.\d+(?:\.\d+)?)", cmd)
            versions.extend(matches)
        return versions

    @staticmethod
    def _check_prerequisites(command: str) -> str | None:
        """检查命令是否需要前置工具。"""
        prereq_map = {
            "pip install": "需要先安装 Python 和 pip",
            "npm install": "需要先安装 Node.js 和 npm",
            "yarn add": "需要先安装 Node.js 和 yarn",
            "pnpm add": "需要先安装 Node.js 和 pnpm",
            "go install": "需要先安装 Go",
            "cargo install": "需要先安装 Rust 和 Cargo",
            "gem install": "需要先安装 Ruby 和 gem",
            "brew install": "需要先安装 Homebrew (macOS)",
            "apt install": "需要 root/sudo 权限",
            "apt-get install": "需要 root/sudo 权限",
            "yum install": "需要 root/sudo 权限",
            "dnf install": "需要 root/sudo 权限",
            "choco install": "需要先安装 Chocolatey (Windows)",
            "scoop install": "需要先安装 Scoop (Windows)",
        }
        for keyword, warning in prereq_map.items():
            if keyword in command.lower():
                return warning
        return None

    # ── 单元测试辅助 ────────────────────────────────────────────────

    def search_tool_in_registry(self, name: str) -> dict | None:
        """在注册表中查找工具（同步，用于测试）。"""
        canonical = name.lower()
        entry = TOOL_REGISTRY.get(canonical)
        if entry and "alias" in entry:
            canonical = entry["alias"].lower()
            entry = TOOL_REGISTRY.get(canonical)
        return entry


# ── 便捷工厂 ───────────────────────────────────────────────────────────

def create_enricher(config: dict | None = None) -> WebEnricher:
    """创建 WebEnricher 实例。"""
    return WebEnricher(config)
