import uuid
import time
from coopgraph.graphs import Graph, Node, Edge
from typing import List, Dict, Tuple
from coopprodsystem.factory.station import Station
from coopstructs.vectors import Vector2
from coopprodsystem.my_dataclasses import content_factory
import logging

logger = logging.getLogger('productionLine')

def transfer_station(from_s: Station, to_s: Station, delay_s: float):
    to_s_space = to_s.space_for_input
    from_avail = from_s.available_output
    if len(from_avail) > 0 and any(to_s_space[(c.resource, c.uom)] > 0 for c in from_avail):
        time.sleep(delay_s)
        logger.info(f"{from_s.id} -> {to_s.id} transferring...")
        for content in from_avail:
            space = to_s_space[(content.resource, content.uom)]
            if space > 0:
                transfer_content = content_factory(content=content, qty=min(space, content.qty))
                from_s.remove_output(content=transfer_content)
                to_s.add_input(inputs=[transfer_content])
        logger.info(f"{from_s.id} -> {to_s.id} transfer complete")

class ProductionLine:
    def __init__(self,
                 init_stations: List[Tuple[Station, Vector2]] = None,
                 init_relationship_map: Dict[Station, List[Station]] = None,
                 id: str = None
                 ):

        self._id = id or uuid.uuid4()
        self._graph = Graph()
        self._stations = set()

        # add init stations:
        if init_stations: self.add_stations(init_stations)

        # add init relationships
        if init_relationship_map: self.add_relationships(init_relationship_map)

    def add_stations(self, stations: List[Tuple[Station, Vector2]]):

        nodes = [Node(station[0].id, station[1]) for station in stations]
        self._stations.add([station[0] for station in stations])

        for node in nodes:
            self._graph.add_node(node)

        logger.info(f"PL {self._id}: Stations added: {[station[0].id for station in stations]}")

    def add_relationships(self, relationships: Dict[Station, List[Station]]):
        edges = []
        for to, froms in relationships.items():
            for fr in froms:
                node_to = self._graph.node_by_name(to.id)
                node_from = self._graph.node_by_name(fr.id)
                edges.append(Edge(node_from, node_to))

        self._graph.add_edges(edges)

        logger.info(f"PL {self._id}: Station relationships added: {[edge for edge in edges]}")

if __name__ == "__main__":
    import logging
    import station_manifest as stations

    pl = ProductionLine()

    format = '%(asctime)s [%(levelname)s]: %(name)s -- %(message)s (%(filename)s:%(lineno)d)'
    logging.basicConfig(format=format, level=logging.INFO)

    generated = []
    while True:
        # s1 short
        shorts = stations.s1.short_inputs
        if len(shorts) > 0:
            time.sleep(4)
            stations.s1.add_input(shorts)

        # s2 short
        shorts = stations.s2.short_inputs
        if len(shorts) > 0:
            time.sleep(4)
            stations.s2.add_input(shorts)

        # available to move?
        transfer_station(from_s=stations.s1, to_s=stations.s3, delay_s=3)
        transfer_station(from_s=stations.s2, to_s=stations.s3, delay_s=2)

        # s3 full
        if len(stations.s3.available_output) > 0:
            time.sleep(3)
            content_removed = stations.s3.remove_output(stations.s3.available_output[0])
            generated.append(content_removed)

        # epoch
        print(sum(x.qty for x in generated))
        time.sleep(.5)

