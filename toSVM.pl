#!/usr/bin/env perl

use v5.14;
use warnings;
use List::Util qw/shuffle/;

my $filename = $ARGV[0] || 'lpl2.tsv';
my $type     = $ARGV[1] || 'ta';
open my $f, '<', $filename or die $!;
open my $o, '>', 'tmp' or die $!;

my $linecount = 0;
my $outputcount = 0;
my @headers;
my @negatives;
while (<$f>) {
    $linecount++;
    next if $linecount == 1;
    chomp;
    my @elems = split /\t/;
    my $id = shift @elems;
    my $origin = shift @elems;
    my $seqlen = shift @elems;
    my $body = "";
    my $feature_num = 1;
    for my $i (0 .. $#elems) {
        for my $j ($i+1 .. $#elems) {
            $body .= $feature_num++ . ":" . ($elems[$i] - $elems[$j]) . " ";
        }
    }
    if ( $origin eq $type ) {
        say $o "+1: $body";
        $outputcount++;
    } else {
        say $o "-1: $body";
    }
}

__END__

my @randomized = shuffle( @negatives );
for my $i ( 0 .. $outputcount - 1 ) {
    say $o $randomized[$i];
}
