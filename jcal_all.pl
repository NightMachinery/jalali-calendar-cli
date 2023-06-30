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

GetOptions("c|color=s" => \$color, "i|indentation=s" => \$indent, "o|outer-indent=s" => \$indent_outer) or die "Error in command line arguments";

#: default values for the options
$color //= -t STDOUT ? "always" : "never";
$indent //= 4;
$indent_outer //= 0;
##

sub strip_ansi {
    my ($string) = @_;
    $string =~ s/\e\[[0-9;]*m//g;  #: this regex matches ANSI escape codes
    return $string;
}

#: Generate the calendar
my @all_threads;  # List to store all thread objects

my $month = 0;
for my $quarter (0..3) {
    my @threads;

    for my $i (1..3) {
        $month = $month + 1;

        push @threads, threads->create(sub {
            my $calendar = `jcal --indentation=$indent --color=$color --no-footnotes --true-color $month $year`;
            chomp $calendar;

            my @lines = split /\n/, $calendar;
            my $length = 0;
            for my $line (@lines) {
                my $len = length strip_ansi($line);
                $length = $len if $len > $length;
            }

            return [\@lines, $length];
        });
    }

    # Store the threads for this quarter
    push @all_threads, \@threads;
}

# Collect the results
for my $quarter_threads (@all_threads) {
    my @calendars = ();
    my $max_length = 0;

    for my $thread (@{$quarter_threads}) {
        my ($calendar_lines, $length) = @{$thread->join()};

        $max_length = $length if $length > $max_length;
        push @calendars, $calendar_lines;
    }

    my $max_len = 0;
    for my $calendar (@calendars) {
        my $len = $#{$calendar};
        $max_len = $len if $len > $max_len;
    }

    for my $i (0..$max_len) {
        print join((' ' x $indent_outer), map { defined $_->[$i] ? sprintf("%-${max_length}s", $_->[$i]) : (' ' x $max_length) } @calendars), "\n";
    }
}
