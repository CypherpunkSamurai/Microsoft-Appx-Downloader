import asyncio
import os
import sys
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
import aiohttp
import msstore

# Initialize rich console
console = Console()


def display_assets_table(assets, is_uwp=True):
    """Display assets in a rich table"""
    table = Table(title="Available Assets")
    table.add_column("No.", style="cyan", no_wrap=True)
    table.add_column("Name", style="magenta")
    table.add_column("Architecture", style="green")
    table.add_column("Extension", style="yellow")
    if is_uwp:
        table.add_column("Modified", style="blue")
    else:
        table.add_column("Locale", style="blue")

    for i, asset in enumerate(assets, 1):
        if is_uwp:
            table.add_row(
                str(i),
                asset["name"],
                asset["arch"],
                asset["extension"],
                asset["modified"]
            )
        else:
            table.add_row(
                str(i),
                asset["name"],
                asset["arch"],
                asset["extension"],
                asset.get("locale", "unknown")
            )

    console.print(table)


async def download_asset(asset, download_dir=None):
    """Download a selected asset with progress display"""
    # Use default downloads directory if not specified
    if download_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        download_dir = os.path.join(script_dir, "downloads")
    
    # Create downloads directory if it doesn't exist
    if not os.path.exists(download_dir):
        os.makedirs(download_dir)

    # Download the selected asset
    file_path = os.path.join(download_dir, asset['name'])
    console.print(f"[yellow]Downloading to:[/yellow] {file_path}")

    try:
        # Create a new session for the download
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=120),
            raise_for_status=False
        ) as session:
            async with session.get(asset['url']) as response:
                if response.status == 200:
                    with open(file_path, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                    console.print("[green]Download completed![/green]")
                    return file_path
                else:
                    console.print(
                        f"[red]Download failed with status {response.status}[/red]")
                    return None
    except Exception as e:
        console.print(f"[red]Download error: {str(e)}[/red]")
        return None


async def main(url, auto_download=False, download_dir=None):
    """Main function to process Microsoft Store URL and list assets"""
    console.print(f"[bold blue]Processing URL:[/bold blue] {url}")
    if auto_download:
        console.print("[bold blue]Auto-download mode enabled[/bold blue]")

    try:
        console.print("[yellow]Getting product information...[/yellow]")
        assets, is_uwp = await msstore.fetch_assets(url)

        # Display assets in a table
        display_assets_table(assets, is_uwp)

        # If auto_download flag is set, download the first asset
        if auto_download:
            if assets:
                selected_asset = assets[0]
                console.print(
                    f"[green]Auto-selecting first asset:[/green] {selected_asset['name']}")
                file_path = await download_asset(selected_asset, download_dir)
                if file_path:
                    console.print(
                        f"[green]Asset downloaded to:[/green] {file_path}")
                    return True
                else:
                    console.print("[red]Failed to download asset[/red]")
                    return False
            else:
                console.print(
                    "[red]No assets available for download[/red]")
                return False

        # Interactive mode - ask user if they want to download any asset
        console.print(
            "\n[yellow]Enter the number of the asset to download, or 'q' to quit:[/yellow]")
        try:
            choice = Prompt.ask("Your choice")

            if choice.lower() == 'q':
                return True

            try:
                index = int(choice) - 1
                if 0 <= index < len(assets):
                    selected_asset = assets[index]
                    console.print(
                        f"[green]Selected:[/green] {selected_asset['name']}")

                    file_path = await download_asset(selected_asset, download_dir)
                    if file_path:
                        console.print(
                            f"[green]Asset downloaded to:[/green] {file_path}")
                        return True
                    else:
                        console.print(
                            "[red]Failed to download asset[/red]")
                        return False
                else:
                    console.print("[red]Invalid selection[/red]")
                    return False
            except ValueError:
                console.print("[red]Invalid input[/red]")
                return False
        except EOFError:
            # Handle non-interactive environments
            console.print(
                "[yellow]Running in non-interactive mode. Use --auto flag to automatically download the first asset.[/yellow]")
            return True

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Microsoft Store Asset Downloader")
    parser.add_argument("url", nargs="?", default="https://apps.microsoft.com/detail/9pdxgncfsczv",
                        help="Microsoft Store URL (default: https://apps.microsoft.com/detail/9pdxgncfsczv)")
    parser.add_argument("--auto", action="store_true",
                        help="Automatically download the first available asset")
    parser.add_argument("--dir", default=None,
                        help="Download directory (default: ./downloads)")

    args = parser.parse_args()

    success = asyncio.run(main(args.url, args.auto, args.dir))

    if not success:
        sys.exit(1)
