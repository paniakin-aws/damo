# SPDX-License-Identifier: GPL-2.0

import argparse
import subprocess

import _damo_dist
import _damo_fmt_str
import _damo_print
import _damo_records
import damo_heatmap
import damo_record_info
import damo_report_footprint
import damo_wss

def fmt_report(args):
    lines = []
    records, err = _damo_records.get_records(record_file=args.access_pattern)
    if err is not None:
        print('access pattern record file (%s) parsing failed (%s)' %
              (args.access_pattern, err))
        exit(1)

    guides = damo_record_info.get_guide_info(records)

    lines.append('Overall recorded access pattern')
    lines.append('===============================')
    lines.append('')
    for guide in guides:
        lines.append('%s' % guide)
    lines.append('')
    lines.append('# regions above are regions that access pattern recorded')
    lines.append('# you can get this via \'damo record_info\', too')

    lines.append('')
    lines.append('Heatmap')
    lines.append('=======')
    lines.append('')
    for guide in guides:
        lines.append('# target %d' % guide.tid)
        for region in guide.regions():
            lines.append('# address range %d-%d' % (region[0], region[1]))
            heatmap = damo_heatmap.fmt_heats(
                    argparse.Namespace(
                        tid=guide.tid, resol=[10, 80],
                        time_range=[guide.start_time, guide.end_time],
                        address_range=region,
                        output='stdout',
                        stdout_colorset='gray',
                        stdout_skip_colorset_example=True,
                        ),
                    records)
            lines.append(heatmap)
    lines.append('# you can get above via \'damo report heatmap\'')

    lines.append('')
    lines.append('Working Set Size and Memory Footprints Distribution')
    lines.append('===================================================')
    lines.append('')

    _damo_records.adjust_records(
            records, aggregate_interval=1, nr_snapshots_to_skip=20)

    if args.footprints is None:
        args.footprints = args.access_pattern + '.mem_footprint'

    for sort_key in ['size', 'time']:
        lines.append('Sorted by %s' % sort_key)
        lines.append('--------------')
        lines.append('')
        wss_dists = damo_wss.get_wss_dists(
                records, acc_thres=1, sz_thres=1, do_sort=sort_key == 'size',
                collapse_targets=True)
        for tid, dists in wss_dists.items():
            # because collapsed targets, only one iteration will be executed here
            output = _damo_dist.fmt_dists(
                    'wss', dists, range(0, 101, 25), pr_all=False,
                    format_fn=_damo_fmt_str.format_sz, raw_number=False,
                    nr_cols_bar=59)
            lines.append(output)
        for metric in ['rss', 'vsz', 'sys_used']:
            fp_dists = damo_report_footprint.get_dists(
                    records=args.footprints, metric=metric,
                    do_sort=sort_key == 'size')
            output = _damo_dist.fmt_dists(
                    metric, fp_dists, range(0, 101, 25), pr_all=False,
                    format_fn=_damo_fmt_str.format_sz, raw_number=False,
                    nr_cols_bar=59)
            lines.append(output)
        lines.append('')
    lines.append('# you can get above via \'damo report wss\' and \'damo report footprints\'')

    lines.append('')
    lines.append('Hotspot functions')
    lines.append('=================')
    lines.append('')

    if args.profile is None:
        args.profile = args.access_pattern + '.profile'

    cmd = ['perf', 'report', '-i', args.profile, '--stdio']
    output = subprocess.check_output(cmd).decode()
    lines.append('\n'.join(output.split('\n')[:30]))

    lines.append('# you can get above via \'damo report profile\'')

    return '\n'.join(lines)

def main(args):
    _damo_print.pr_with_pager_if_needed(fmt_report(args))

def set_argparser(parser):
    parser.add_argument(
            '--access_pattern', metavar='<file>', default='damon.data',
            help='access pattern record file')
    parser.add_argument(
            '--footprints', metavar='<file>',
            help='memory footprints record file')
    parser.add_argument(
        '--profile', metavar='<file>', help='profile record file')
    parser.description = 'Show a holistic access pattern report'
