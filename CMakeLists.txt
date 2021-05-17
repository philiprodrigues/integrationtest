cmake_minimum_required(VERSION 3.12)
project(integrationtest VERSION 0.0.1)

find_package(daq-cmake REQUIRED)

daq_setup_environment()

daq_install()
