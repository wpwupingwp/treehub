#!/usr/bin/perl
# TreeBase dump tree file

use strict;
use DBI;

use Bio::Phylo::Factory;

my $database = "treebasedmp";
my $username = 'root';
my $password = '123456';
my $host = "localhost";

# Feed script with a list of node_ids
my @node_ids = @ARGV;
@node_ids = split(/,/,join(',',@node_ids));

my $dbh = &ConnectToPg($database, $username, $password, $host);

my %obj_by_name;
my ($fac, $proj, $forest, $tree);

# Query to return all parent-child node_ids that 
# descend from a given node_id
my $tree_table_statement = <<STATEMENT;
SELECT np.child_path_id AS child_id, ce.parent_id AS parent_id, 
COALESCE( CAST(ce.edge_length AS numeric), 0) AS child_length, ce.edge_support AS child_support, 
cn.node_label AS child_label, COALESCE( CAST(pe.edge_length AS numeric), 0) AS parent_length, 
pe.edge_support AS parent_support, (cn.right_id - cn.left_id) - 1 AS internal
FROM node_path np 
JOIN edges ce ON (np.child_path_id = ce.child_id) 
JOIN nodes cn ON (np.child_path_id = cn.node_id) 
JOIN nodes pn ON (ce.parent_id = pn.node_id) 
LEFT JOIN edges pe ON (pn.node_id = pe.child_id) 
WHERE np.parent_path_id = ?  
STATEMENT
my $tree_table = $dbh->prepare ($tree_table_statement);

# Query to test whether the recovered tree is a phylogeny with 
# branch lengths or a cladogram without branch lengths
my $sum_of_edge_lengths_statement = <<STATEMENT;
SELECT COALESCE( SUM( CAST (e.edge_length AS numeric) ), 0 ) 
FROM edges e JOIN nodes n ON (e.child_id = n.node_id) 
WHERE n.tree_id = ? 
STATEMENT

# Build a project in Bio::Phylo containing a forest
$fac = Bio::Phylo::Factory->new;
$proj = $fac->create_project;
$forest = $fac->create_forest;
$proj->insert( $forest );

my $statement = "SELECT tree_id, node_id FROM nodes WHERE "; 
$statement .= "node_id IN ( " . join(', ',@node_ids) . " ) ";

my $get_trees = $dbh->prepare($statement) or die "Can't prepare $statement: $dbh->errstr\n";    
my $rv = $get_trees->execute or die "can't execute the query: $get_trees->errstr\n";

# Loop over the list of node_id values supplied to the script
while (my ($tree_id, $start_node_id) = $get_trees->fetchrow_array) {

  # create a tree object and add it to the forest
  $tree = $fac->create_tree;
  $forest->insert( $tree );
  $tree->set_name( "tree $tree_id starting at node $start_node_id" );

  # calculate the sum of all branch lengths; if this sums to zero, it must be a cladogram
  my $sumbrlengths = $dbh->selectrow_array ("$sum_of_edge_lengths_statement", undef, $tree_id);

  $tree_table->execute($start_node_id);

  # Loop over each pair of parent-child nodes, adding node objects to the tree
  for my $row (@{$tree_table->fetchall_arrayref}) {
    my ($child_id, $parent_id, $child_length, $child_support, $child_label, $parent_length, $parent_support, $internal) = @$row;

    if ($sumbrlengths) {
      $obj_by_name{$child_id} = $fac->create_node( -name => $child_label, -branch_length => $child_length );
    } else {
      $obj_by_name{$child_id} = $fac->create_node( -name => $child_label );
    }
    $tree->insert( $obj_by_name{$child_id} );
    
    if ( not exists $obj_by_name{$parent_id} ) { 
      if ($sumbrlengths) {
        $obj_by_name{$parent_id} = $fac->create_node( -branch_length => $parent_length );
      } else {
        $obj_by_name{$parent_id} = $fac->create_node( );
      }
      $tree->insert( $obj_by_name{$parent_id} );
    }
    $obj_by_name{$child_id}->set_parent( $obj_by_name{$parent_id} );
  }
}

# Write tree file using the NEXUS format
my $treeout = $proj->to_nexus( '-nodelabels' => 1 );
$treeout =~ s/\)Node\d+/)/g;
print "$treeout\n\n";
my $rc = $dbh->disconnect;
exit;

# Connect to Postgres using DBI
#==============================================================
sub ConnectToPg {

    my ($cstr, $user, $pass, $host) = @_;
 
    $cstr = "DBI:Pg:dbname="."$cstr";
    $cstr .= ";host=$host";
 
    my $dbh = DBI->connect($cstr, $user, $pass, {PrintError => 1, RaiseError => 1});
    $dbh || &error("DBI connect failed : ",$dbh->errstr);

    return($dbh);
}

