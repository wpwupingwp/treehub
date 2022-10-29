from sys import getsizeof as sizeof
from timeit import default_timer as timer


def get_parent_info():
    ncbi_nodes = open('ncbi_nodes', 'r')
    species = []
    son_parent = dict()
    id_rank = dict()
    species_genus = dict()
    species_family = dict()
    species_order = dict()
    for line in ncbi_nodes:
        tax_id, parent_id, rank, *_ = line.split('|')
        son_parent[tax_id] = parent_id
        id_rank[tax_id] = rank
        if rank == 'species':
            species.append(tax_id)
    id_rank['0'] = 'root'
    #
    species_lineage = list()
    for s in species:
        lineage = [s]
        parent_rank = ''
        parent = -1
        while parent_rank != 'root' and s != '0':
            parent = son_parent[s]
            parent_rank = id_rank[parent]
            lineage.append(parent)
            # if parent_rank == 'order': break
            s = parent
        species_lineage.append(lineage)
    test = '4530'
    print(test)
    print(id_rank[test])
    print(son_parent[test])
    for lineage in species_lineage:
        s = lineage[0]
        for parent in lineage[1:]:
            parent_rank = id_rank[parent]
            if parent_rank == 'genus':
                species_genus[s] = parent
            elif parent_rank == 'family':
                species_family[s] = parent
            elif parent_rank == 'order':
                species_order[s] = parent
                break
    print('son_parent', sizeof(son_parent))
    print('id_rank', sizeof(id_rank))
    print('species', sizeof(species))
    print('species_genus', sizeof(species_genus))
    print('species_family', sizeof(species_family))
    print('species_order', sizeof(species_order))
    with open('species_info', 'w') as _:
        for s in species:
            genus = species_genus.get(s, '')
            family = species_family.get(s, '')
            order = species_order.get(s, '')
            line = f'{s}|{genus}|{family}|{order}\n'
            _.write(line)
    return


if __name__ == '__main__':
    start = timer()
    get_parent_info()
    end = timer()
    print(end-start, 'seconds')
