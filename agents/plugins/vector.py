#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2024 Marius Rieder <marius.rieder@durchmesser.ch> - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import urllib.request
from functools import cached_property


class VectorApi:
    def __init__(self, url):
        self.url = url

    def _payload(self, **kwargs):
        graphql = json.dumps(dict(**kwargs))
        return bytes(graphql, 'utf-8')

    @cached_property
    def server_info(self):
        graphql = self._payload(query=r'{ health meta { versionString } sources { totalCount } transforms { totalCount } sinks { totalCount } }')
        with urllib.request.urlopen(self.url, data=graphql) as f:
            data = json.load(f)['data']
            return dict(
                health=data['health'],
                version=data['meta']['versionString'],
                sources=data['sources']['totalCount'],
                transforms=data['transforms']['totalCount'],
                sinks=data['sinks']['totalCount'],
            )

    def components(self, type, metrics):
        start = None
        while True:
            graphql = self._payload(query=f"""
            {{ {type}{f'(after:"{start}")' if start else ''} {{
                pageInfo {{ hasNextPage endCursor }}
                nodes {{
                    componentId
                    componentType
                    metrics {{ {" ".join(f'{m} {{ {m} }}' for m in metrics)} }}
                }}
            }} }}""")

            with urllib.request.urlopen(self.url, data=graphql) as f:
                data = json.load(f)['data']
                for node in data[type]['nodes']:
                    node.update({
                        k: int(v[k])
                        for k, v in node.pop('metrics', {}).items()
                        if v
                    })
                    yield node
                if not data[type]['pageInfo']['hasNextPage'] or data[type]['pageInfo']['endCursor'] is None:
                    return
                start = data[type]['pageInfo']['endCursor']

    @staticmethod
    def metric_to_list(metric):
        return [
            str(int(metric[key][key])) if key in metric and metric[key] else ""
            for key in (
                'receivedBytesTotal',
                'receivedEventsTotal',
                'sentEventsTotal',
                'sentBytesTotal',
            )
        ]


def main():
    vector = VectorApi("http://0.0.0.0:8686/graphql")

    print('<<<vector>>>')
    print(json.dumps(vector.server_info, separators=(',', ':')))

    print('<<<vector_source>>>')
    for source in vector.components('sources', ['receivedBytesTotal', 'receivedEventsTotal', 'sentEventsTotal']):
        print(json.dumps(source, separators=(',', ':')))

    print('<<<vector_transform>>>')
    for transform in vector.components('transforms', ['receivedEventsTotal', 'sentEventsTotal']):
        print(json.dumps(transform, separators=(',', ':')))

    print('<<<vector_sink>>>')
    for sink in vector.components('sinks', ['receivedEventsTotal', 'sentEventsTotal', 'sentBytesTotal']):
        print(json.dumps(sink, separators=(',', ':')))


if __name__ == "__main__":
    main()
