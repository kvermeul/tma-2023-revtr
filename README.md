# Planning
This tutorial is divided in two parts: a tutorial and lesson about how Reverse Traceroute works, and  describe how we can use it to troubleshoot 
paths and use the PEERING platform to show an example of Traffic Engineering.

The second part will be to put your hands on using the REVTR 2.0 system which is an [Internet scale Reverse Traceroute](https://dl.acm.org/doi/pdf/10.1145/3517745.3561422) system.

# Troubleshooting paths with Reverse Traceroute
In this tutorial, you will put yourself in the shoes of an operator who wants
to monitor some network paths.

## Q1. Find a problem in the network.

Here is a list of ping measurements that we run for you between PEERING servers to some destinations.
This is similar to what an operator would do as a first step to troubleshoot potential problems between their servers and their clients. 

We give you the geolocation of the servers and the destinations.

Can you identify some suspicious 
paths with inflated RTTs? 

## Q2. Identify the cause of the problem with REVTR 2.0 

Use the functions of the script example.py to fetch the results of some reverse traceroutes 
that we have already run. 

Use the batch ids (...) and the function fetch_revtrs(batch_id) to fetch the corresponding measurements.

Can you find which AS is problematic and how you could fix the problem? 

## Q3. Change the PEERING announcement to fix the problem 

## Q4. Check that you fixed the problem with REVTR 2.0
The last step is to check whether your configuration change has fixed the problem.

Using the function run_revtrs(source_destination_pair, label) in the example, re-run 
the reverse traceroutes and analyze the paths and the RTT measurements. 
Is that better?

## Q5. Another example: load balancing





