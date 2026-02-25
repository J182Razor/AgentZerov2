"""Git Sync Tool for Agent Zero

Provides automatic version control by committing and pushing changes to GitHub.
Call this tool after significant changes to maintain version history.
"""

from python.helpers.tool import Tool, Response
from python.helpers.git_auto_sync import get_syncer


class GitSync(Tool):
 """Sync changes to GitHub for version control"""

 async def execute(
 self,
 message: str = "",
 auto: bool = True,
 **kwargs
 ) -> Response:
 syncer = get_syncer()
 
 # Get current status
 status = syncer.get_status()
 
 if not status["has_changes"]:
 return Response(
 message="✅ No changes to sync. Repository is up to date.",
 break_loop=False
 )
 
 # Generate commit message if not provided
 if not message:
 from datetime import datetime
 timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
 changed_count = len(status["changed_files"])
 message = f"Auto-sync: {changed_count} files changed at {timestamp}"
 
 # Sync (commit + push)
 result = syncer.sync(message)
 
 if result["pushed"]:
 return Response(
 message=f"✅ Successfully synced to GitHub!\n"
 f"Commit: {message}\n"
 f"Files: {len(status['changed_files'])} changed",
 break_loop=False
 )
 elif result["committed"]:
 return Response(
 message=f"⚠️ Committed but push failed. Check network connection.",
 break_loop=False
 )
 else:
 return Response(
 message=f"❌ Sync failed: {result.get('error', 'Unknown error')}",
 break_loop=False
 )


class GitStatus(Tool):
 """Check git status without syncing"""

 async def execute(self, **kwargs) -> Response:
 syncer = get_syncer()
 status = syncer.get_status()
 
 if status["has_changes"]:
 files = "\n".join(f" - {f}" for f in status["changed_files"][:20])
 more = f"\n ... and {len(status['changed_files']) - 20} more" if len(status["changed_files"]) > 20 else ""
 return Response(
 message=f"📝 Uncommitted changes ({len(status['changed_files'])} files):\n{files}{more}",
 break_loop=False
 )
 else:
 return Response(
 message="✅ Repository is clean. No uncommitted changes.",
 break_loop=False
 )
