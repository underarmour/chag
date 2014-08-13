import json as j
import subprocess
import tempfile
import time


import click
from chag.changelog import get_tag, get_tags


def get_click_tag(file, tag, border):
    try:
        return get_tag(file, tag, border)
    except Exception:
        raise click.ClickException('%s not found in %s' % (tag, file.name))


def git_is_clean():
    try:
        cmd = 'git diff --stat --exit-code'.split(' ')
        subprocess.check_call(cmd)
        cmd.append('--cached')
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as e:
        raise click.ClickException('Your repository is not clean')


@click.group()
@click.pass_context
def main(ctx):
    pass


@main.command()
@click.option('--border', default='-', help='Repeated border character')
@click.argument('file', type=click.File('rb'))
@click.argument('tag')
def contents(file, tag, border):
    """Returns the changelog contents for the provided TAG from the FILE.
    Pass 'latest' as the TAG to parse the first found tag.

    \b
    Examples:
      chag contents CHANGELOG latest
      chag contents CHANGELOG 0.1.0
      chag contents --border='=' CHANGELOG 0.1.0
    """
    found = get_click_tag(file, tag, border)
    click.echo(found['contents'])


@main.command()
@click.option('--border', default='-', help='Repeated border character')
@click.option('--json/--no-json', default=False,
              help='Determines if JSON or just the version is returned.')
@click.argument('file', type=click.File('rb'))
@click.argument('tag')
def get(file, tag, border, json):
    """Prints out JSON data for a specific TAG found in FILE. Pass 'latest'
    as the TAG to parse the first found tag entry in the changelog. The
    JSON output contains the following keys:

    \b
    - line_number: Line that the tag heading is found
    - full_heading: The full heading line
    - tag: Just the tag from the heading (e.g., '0.1.0')
    - contents: The text content of the changelog entry

    \b
    Examples:
      chag get CHANGELOG 0.0.1
      chag get CHANGELOG latest
      chag get --border='=' CHANGELOG 1.0.0-rc2
      chag get --json CHANGELOG latest
    """
    found = get_click_tag(file, tag, border)
    if json:
        click.echo(j.dumps(found))
    else:
        click.echo(found['tag'])


@main.command()
@click.option('--border', default='-', help='Repeated border character')
@click.argument('file', type=click.File('rb'))
def list(file, border):
    """Lists the tag versions available in a changelog file

    \b
    Examples:
      chag list CHANGELOG
      chag list --border='=' CHANGELOG
    """
    for tag in get_tags(file, border):
        print(tag['tag'])


@main.command()
@click.option('--border', default='-', help='Repeated border character')
@click.argument('file', type=click.File('rb'))
@click.argument('heading')
def update(file, heading, border):
    """Replaces the latest changelog entry in FILE with the provided
    HEADING (e.g., '1.0.1 ()'). If the last two characters of HEADING
    are '()', they will be converted to today's date formatted as
    '(YYYY-MM-DD)'.

    \b
    Examples:
      chag update CHANGELOG.rst '1.0.1'
      chag update CHANGELOG.rst '1.0.1 ()'
      chag update --border='=' CHANGELOG.rst '1.0.1 ()'
    """
    found = get_click_tag(file, 'latest', border)
    if heading[-2::] == '()':
        replacement = '(' + time.strftime('%Y-%m-%d') + ')'
        heading = heading.replace('()', replacement)
    file.seek(0)
    lines = file.readlines()
    lines[found['line_number']] = heading + "\n"
    lines[found['line_number'] + 1] = (border * len(heading)) + "\n"
    with open(file.name, 'w') as f:
        f.write(''.join(lines))


@main.command()
@click.option('--border', default='-', help='Repeated border character')
@click.option('--v-prefix/--no-v-prefix', default=False)
@click.option('--sign/--no-sign', default=False)
@click.option('--force/--no-force', default=False)
@click.argument('file', type=click.File('rb'))
def tag(file, border, v_prefix, sign, force):
    """Creates an annotated git tag from the latest changelog entry in the
    provided FILE. The tag uses the version number found in the changelog
    entry's header line and the contents of the changelog entry as the tag
    annotation.

    \b
    Examples:
      chag tag /path/to/CHANGELOG.md
      chag tag --v-prefix CHANGELOG.rst
      chag tag --sign CHANGELOG.rst
      chag tag --force CHANGELOG.md
      chag tag --debug CHANGELOG.md
    """
    found = get_click_tag(file, 'latest', border)
    if found['tag'] == 'Next':
        raise click.ClickException('Not tagging a "Next Release" entry!')
    click.echo('Ensuring git repository is clean with git diff', err=True)
    git_is_clean()
    if v_prefix:
        tag_name = 'v' + found['tag']
    else:
        tag_name = found['tag']
    args = ['git', 'tag']
    if force:
        args.append('--force')
    if sign:
        args.append('--sign')
    args.append('-a')
    args.append('-F')
    args.append('-')
    args.append(tag_name)

    click.echo('Creating a git tag for ' + tag_name)
    click.echo("Using the following annotation:", err=True)
    click.echo('  ' + found['contents'].replace("\n", "\n  "), err=True)
    tmp = tempfile.TemporaryFile()
    tmp.write(found['contents'])
    tmp.seek(0)

    try:
        subprocess.check_call(args, stdin=tmp)
    except subprocess.CalledProcessError as e:
        click.echo('Git tag failed: ' + str(e))
    finally:
        tmp.close()


if __name__ == '__main__':
    main()