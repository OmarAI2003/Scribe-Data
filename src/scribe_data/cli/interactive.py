"""
Interactive mode functionality for the Scribe-Data CLI to allow users to select request arguments.

.. raw:: html
    <!--
    * Copyright (C) 2024 Scribe
    *
    * This program is free software: you can redistribute it and/or modify
    * it under the terms of the GNU General Public License as published by
    * the Free Software Foundation, either version 3 of the License, or
    * (at your option) any later version.
    *
    * This program is distributed in the hope that it will be useful,
    * but WITHOUT ANY WARRANTY; without even the implied warranty of
    * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    * GNU General Public License for more details.
    *
    * You should have received a copy of the GNU General Public License
    * along with this program.  If not, see <https://www.gnu.org/licenses/>.
    -->
"""

import logging
from pathlib import Path
from typing import List

import questionary
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from questionary import Choice
from rich import print as rprint
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from tqdm import tqdm
from scribe_data.cli.total import total_wrapper
from scribe_data.cli.list import list_wrapper
from scribe_data.cli.get import get_data
from scribe_data.cli.version import get_version_message
from scribe_data.utils import (
    DEFAULT_JSON_EXPORT_DIR,
    data_type_metadata,
    language_metadata,
    list_all_languages,
)

# MARK: Config Setup

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(markup=True)],  # Enable markup for colors
)
console = Console()
logger = logging.getLogger("rich")
MESSAGE = "[bold cyan]Thank you for using Scribe-Data![/bold cyan]"


class ScribeDataConfig:
    def __init__(self):
        self.languages = list_all_languages(language_metadata)
        self.data_types = list(data_type_metadata.keys())
        self.selected_languages: List[str] = []
        self.selected_data_types: List[str] = []
        self.output_type: str = "json"
        self.output_dir: Path = Path(DEFAULT_JSON_EXPORT_DIR)
        self.overwrite: bool = False
        self.configured: bool = False


config = ScribeDataConfig()


# MARK: Summary


def display_summary():
    """
    Displays a summary of the interactive mode request to run.
    """
    table = Table(
        title="Scribe-Data Request Configuration Summary", style="bright_white"
    )

    table.add_column("Setting", style="bold cyan", no_wrap=True)
    table.add_column("Value(s)", style="magenta")

    table.add_row("Languages", ", ".join(config.selected_languages) or "None")
    table.add_row("Data Types", ", ".join(config.selected_data_types) or "None")
    table.add_row("Output Type", config.output_type)
    table.add_row("Output Directory", str(config.output_dir))
    table.add_row("Overwrite", "Yes" if config.overwrite else "No")

    console.print("\n")
    console.print(table, justify="left")
    console.print("\n")


def configure_settings():
    """
    Configures the settings of the interactive mode request.

    Asks for:
        - Languages
        - Data types
        - Output type
        - Output directory
        - Whether to overwrite
    """
    rprint(
        "[cyan]Follow the prompts below. Press tab for completions and enter to select.[/cyan]"
    )
    # MARK: Languages
    language_completer = WordCompleter(["All"] + config.languages, ignore_case=True)
    initial_language_selection = ", ".join(config.selected_languages)
    selected_languages = prompt(
        "Select languages (comma-separated or type 'All'): ",
        default=initial_language_selection,
        completer=language_completer,
    )

    if "All" in selected_languages:
        config.selected_languages = config.languages
    else:
        config.selected_languages = [
            lang.strip()
            for lang in selected_languages.split(",")
            if lang.strip() in config.languages
        ]

    if not config.selected_languages:
        rprint("[yellow]No language selected. Please try again.[/yellow]")
        return configure_settings()

    # MARK: Data Types
    data_type_completer = WordCompleter(["All"] + config.data_types, ignore_case=True)
    initial_data_type_selection = ", ".join(config.selected_data_types)
    selected_data_types = prompt(
        "Select data types (comma-separated or type 'All'): ",
        default=initial_data_type_selection,
        completer=data_type_completer,
    )

    if "All" in selected_data_types.capitalize():
        config.selected_data_types = config.data_types
    else:
        config.selected_data_types = [
            dt.strip()
            for dt in selected_data_types.split(",")
            if dt.strip() in config.data_types
        ]

    if not config.selected_data_types:
        rprint("[yellow]No data type selected. Please try again.[/yellow]")
        return configure_settings()

    # MARK: Output Type
    output_type_completer = WordCompleter(["json", "csv", "tsv"], ignore_case=True)
    config.output_type = prompt(
        "Select output type (json/csv/tsv): ", completer=output_type_completer
    )
    while config.output_type not in ["json", "csv", "tsv"]:
        rprint("[yellow]Invalid output type selected. Please try again.[/yellow]")
        config.output_type = prompt(
            "Select output type (json/csv/tsv): ", completer=output_type_completer
        )

    # MARK: Output Directory
    if output_dir := prompt(f"Enter output directory (default: {config.output_dir}): "):
        config.output_dir = Path(output_dir)

    # MARK: Overwrite Confirmation
    overwrite_completer = WordCompleter(["Y", "n"], ignore_case=True)
    overwrite = (
        prompt("Overwrite existing files? (Y/n): ", completer=overwrite_completer)
        or "y"
    )
    config.overwrite = overwrite.lower() == "y"

    config.configured = True
    display_summary()


def run_request():
    """
    Runs the interactive mode request given the configuration.
    """
    if not config.selected_languages or not config.selected_data_types:
        rprint("[bold red]Error: Please configure languages and data types.[/bold red]")
        return

    # Calculate total operations
    total_operations = len(config.selected_languages) * len(config.selected_data_types)

    # MARK: Export Data
    with tqdm(
        total=total_operations,
        desc="Exporting data",
        unit="operation",
    ) as pbar:
        for language in config.selected_languages:
            for data_type in config.selected_data_types:
                pbar.set_description(f"Exporting {language} {data_type} data")

                if get_data(
                    language=language,
                    data_type=data_type,
                    output_type=config.output_type,
                    output_dir=str(config.output_dir),
                    overwrite=config.overwrite,
                    interactive=True,
                ):
                    logger.info(
                        f"[green]✔ Exported {language} {data_type} data.[/green]"
                    )

                else:
                    logger.info(
                        f"[red]✘ Failed to export {language} {data_type} data.[/red]"
                    )

                pbar.update(1)

    if config.overwrite:
        rprint("[bold green]Data request completed successfully![/bold green]")


# MARK: Start


def request_total_lexeme():
    """
    Requests language and data type for lexeme totals.
    """
    # MARK: Language Selection
    language_completer = WordCompleter(["All"] + config.languages, ignore_case=True)
    initial_language_selection = ", ".join(config.selected_languages)
    selected_languages = prompt(
        "Select languages (comma-separated or 'All'): ",
        default=initial_language_selection,
        completer=language_completer,
    )
    if "All" in selected_languages:
        config.selected_languages = config.languages
    elif selected_languages.strip():  # Check if input is not just whitespace
        config.selected_languages = [
            lang.strip()
            for lang in selected_languages.split(",")
            if lang.strip() in config.languages
        ]

    if not config.selected_languages:
        rprint("[yellow]No language selected. Please try again.[/yellow]")
        return request_total_lexeme()

    # MARK: Data Type Selection
    data_type_completer = WordCompleter(["All"] + config.data_types, ignore_case=True)
    initial_data_type_selection = ", ".join(config.selected_data_types)
    selected_data_types = prompt(
        "Select data types (comma-separated or 'All'): ",
        default=initial_data_type_selection,
        completer=data_type_completer,
    )
    if "All" in selected_data_types.capitalize():
        config.selected_data_types = config.data_types
    elif selected_data_types.strip():  # Check if input is not just whitespace
        config.selected_data_types = [
            dt.strip()
            for dt in selected_data_types.split(",")
            if dt.strip() in config.data_types
        ]

    if not config.selected_data_types:
        rprint("[yellow]No data type selected. Please try again.[/yellow]")
        return request_total_lexeme()


def request_total_lexeme_loop():
    """
    Continuously prompts for lexeme requests until exit.
    """
    while True:
        choice = questionary.select(
            "What would you like to do?",
            choices=[
                Choice("Request total lexeme", "total"),
                Choice("Run for total lexeme", "run"),
                Choice("Exit", "exit"),
            ],
        ).ask()

        if choice == "run":
            total_wrapper(
                language=config.selected_languages,
                data_type=config.selected_data_types,
                all_bool=False,
            )
            config.selected_languages, config.selected_data_types = [], []
            rprint(MESSAGE)
            break
        elif choice == "exit":
            return
        else:
            # config.selected_languages, config.selected_data_types = [], []
            request_total_lexeme()


def see_list_languages():
    """
    See list of languages.
    """

    choice = questionary.select(
        "What would you like to list?",
        choices=[
            Choice("All languages", "all_languages"),
            Choice("Languages for a specific data type", "languages_for_data_type"),
            Choice("Data types for a specific language", "data_types_for_language"),
        ],
    ).ask()

    if choice == "all_languages":
        list_wrapper(all_bool=True)
    elif choice == "languages_for_data_type":
        list_wrapper(data_type=True)
    elif choice == "data_types_for_language":
        list_wrapper(language=True)


def start_interactive_mode():
    """
    Entry point for interactive mode.
    """
    rprint(
        f"[bold cyan]Welcome to {get_version_message()} interactive mode![/bold cyan]"
    )
    while True:
        # Check if both selected_languages and selected_data_types are empty
        if not config.selected_languages and not config.selected_data_types:
            choices = [
                Choice("Request get data", "configure"),
                Choice("Request total lexeme", "total"),
                Choice("See list of languages", "languages"),
                Choice("Exit", "exit"),
            ]
        else:
            choices = [
                Choice("Request get data", "configure"),
                Choice("Exit", "exit"),
            ]
            if config.configured:
                choices.insert(1, Choice("Run configured data request", "run"))
            else:
                choices.insert(1, Choice("Request total lexeme", "total"))

        choice = questionary.select("What would you like to do?", choices=choices).ask()

        if choice == "configure":
            configure_settings()
        elif choice == "total":
            request_total_lexeme()
            request_total_lexeme_loop()
            break
        elif choice == "languages":
            see_list_languages()
            break
        elif choice == "run":
            run_request()
            rprint(MESSAGE)
            break
        else:
            rprint(MESSAGE)
            break


if __name__ == "__main__":
    start_interactive_mode()
