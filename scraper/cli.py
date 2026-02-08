"""
Command-line interface for LLM Web Scraper.

Usage:
    scraper scrape URL [--domain DOMAIN] [--page-type TYPE]
    scraper --help
"""

import asyncio
import click
import json
import logging

from scraper.config import container
from scraper.use_cases.scrape_page import ScrapePage
from scraper.domain.models import PageType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="2.0.0", prog_name="llm-scraper")
def cli():
    """LLM Web Scraper - Intelligent web scraping with XPath and LLM fallback."""
    pass


@cli.command()
@click.argument("url")
@click.option("--domain", "-d", help="Domain name (auto-detected if not provided)")
@click.option(
    "--page-type",
    "-t",
    type=click.Choice([pt.value for pt in PageType if pt != PageType.UNKNOWN]),
    help="Page type (auto-detected if not provided)",
)
@click.option("--output", "-o", type=click.Choice(["json", "table"]), default="json")
def scrape(url: str, domain: str, page_type: str, output: str):
    """
    Scrape a single page.

    Examples:
        scraper scrape https://example.com/team
        scraper scrape https://example.com/team -d example.com -t team_page
    """
    # Extract domain from URL if not provided
    if not domain:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc

    # Convert page_type string to enum
    page_type_enum = None
    if page_type:
        page_type_enum = PageType(page_type)

    # Create ScrapePage use case
    use_case = ScrapePage(
        fetcher=container.fetcher,
        llm=container.llm,
        storage=container.storage,
        alerting=container.alerting,
    )

    # Execute
    click.echo(f"Scraping: {url}")
    click.echo(f"Domain: {domain}")

    result = asyncio.run(
        use_case.execute(
            url=url,
            domain=domain,
            page_type=page_type_enum,
        )
    )

    # Output results
    if result.success:
        click.echo(click.style("Success!", fg="green", bold=True))

        if output == "json":
            click.echo(json.dumps(result.data, indent=2, default=str))
        else:
            # Table format
            for key, value in result.data.items():
                click.echo(f"  {key}: {value}")

        click.echo(f"\nHTML saved: {result.html_path}")
        click.echo(f"JSON saved: {result.json_path}")
        click.echo(f"Method: {result.extraction_method.value}")
    else:
        click.echo(click.style("Failed!", fg="red", bold=True))
        click.echo(f"Error: {result.error_message}")


@cli.command()
def info():
    """Show current configuration."""
    import os

    click.echo("LLM Web Scraper Configuration")
    click.echo("=" * 40)
    click.echo(f"FETCHER: {os.getenv('FETCHER', 'httpx')}")
    click.echo(f"STORAGE: {os.getenv('STORAGE', 'local')}")
    click.echo(f"LLM_PROVIDER: {os.getenv('LLM_PROVIDER', 'direct')}")
    click.echo(f"ALERTING: {os.getenv('ALERTING', 'console')}")
    click.echo(f"DATA_PATH: {os.getenv('DATA_PATH', 'data')}")

    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if api_key:
        click.echo(f"ANTHROPIC_API_KEY: {'*' * 8}...{api_key[-4:]}")
    else:
        click.echo(click.style("ANTHROPIC_API_KEY: NOT SET", fg="yellow"))


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()
