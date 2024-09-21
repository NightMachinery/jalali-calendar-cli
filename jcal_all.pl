#!/usr/bin/env perl
use strict;
use warnings;
use v5.34.0;
use threads;
use feature 'refaliasing';
use Getopt::Long;
no warnings 'experimental::refaliasing';
use constant false => 0;
use constant true  => 1;


my $year = shift || die "Please specify a Jalali year as argument.\n";

##
my $color;
my $indent;
my $indent_outer;
my $indent_horizontal;
my $line_prefix;

GetOptions("c|color=s" => \$color, "i|indentation=s" => \$indent, "o|outer-indent=s" => \$indent_outer, "h|horizontal-indent=s" => \$indent_horizontal, "p|line-prefix=s" => \$line_prefix) or die "Error in command line arguments";

#: default values for the options
$color //= -t STDOUT ? "always" : "never";

# $indent_horizontal //= 0;
$indent_horizontal //= 1;

# $indent //= 4;
# $indent_outer //= 0;
# $line_prefix //= " ";

$indent //= 4;
$indent_outer //= 2;
$line_prefix //= ""; #: We need the screen real estate.

# $indent //= 3;
# $indent_outer //= 2;
# $line_prefix //= " ";
##

sub strip_ansi {
    my ($string) = @_;
    $string =~ s/\e\[[0-9;]*m//g;  #: this regex matches ANSI escape codes
    return $string;
}

my @all_threads;
#: List of list of threads (list of quarters which are lists of months)

my $month = 0;
for my $quarter (0..3) {
    my @threads;

    for my $i (1..3) {
        $month = $month + 1;

        push @threads, threads->create(sub {
            open(my $calendar, '-|', 'jcal', "--indentation=$indent", "--color=$color", "--line-prefix=$line_prefix", "--no-footnotes", "--true-color", $month, $year) or die "could not execute jcal";

            my @lines;
            my $length = 0;
            ##
            # my $calendar = `jcal --indentation=$indent --color=$color --line-prefix=$line_prefix --no-footnotes --true-color $month $year`;
            # chomp $calendar;
            # @lines = split /\n/, $calendar;
            # for my $line (@lines) {
            #     my $len = length strip_ansi($line);
            #     $length = $len if $len > $length;
            # }
            ##

            while (<$calendar>) {
                chomp;
                push(@lines, $_);
                my $len = length strip_ansi($_);
                $length = $len if $len > $length;
            }
            close($calendar);

            return [\@lines, $length];
                                       });
    }

    #: Store the threads for this quarter
    push @all_threads, \@threads;
}

#: Collect the results
for my $quarter (0 .. $#all_threads) {
    my $quarter_threads = $all_threads[$quarter];

    my @calendars = ();
    #: =calendars= is a list (months) of list of strings (rows of each month).
    #: I.e., each calendar is a single month.

    my $max_row_length = 0;
    #: max row length of the current quarter (between the three months)

    for my $thread (@{$quarter_threads}) {
        my ($calendar_lines, $length) = @{$thread->join()};

        $max_row_length = $length if $length > $max_row_length;
        push @calendars, $calendar_lines;
    }

    my $max_height_len = 0; #: max height of the current quarter
    for my $calendar (@calendars) {
        my $len = $#{$calendar};
        $max_height_len = $len if $len > $max_height_len;
    }

    for my $i (0..$max_height_len) {
        print join((' ' x $indent_outer), map { defined $_->[$i] ? sprintf("%-${max_row_length}s", $_->[$i]) : (' ' x $max_row_length) } @calendars), "\n";
    }

    #: Print a newline between quarters
    print("\n" x $indent_horizontal) if $quarter < 3;
    #: There are a total of four quarters, and we don't want the separator for the last quarter.
}
