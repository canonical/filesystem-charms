Feature: Lustre server operations
  Validate the lustre-server charm deployment and operations.


  @functional @edge
  Scenario: Deploy a minimal two-unit lustre-server cluster
    Given I add model 'lustre'
    And I switch to model 'lustre'
    And I disable secureboot on the LXD profile for model 'lustre'
    And I pack a 'lustre-server' charm from project directory '.'
    And I deploy 'lustre-server' from a local charm located at 'lustre-server.charm' on base 'ubuntu@26.04' with '2' units with constraints 'virt-type=virtual-machine cores=4 mem=4G'
    And I add storage 'mgt-mdt' to unit 'lustre-server/0' from pool 'loop' of size '1G' with '2' instances
    And I add storage 'ost' to unit 'lustre-server/1' from pool 'loop' of size '1G' with '3' instances
    And '2' instances of storage 'mgt-mdt' are attached to unit 'lustre-server/0'
    And '3' instances of storage 'ost' are attached to unit 'lustre-server/1'
    Then the workload status for app 'lustre-server' is 'active'
    And all agents are 'idle' in model 'lustre'

  @functional @edge
  Scenario: MGS+MDS and OSS services are running
    Given 'lustre-server' is deployed
    When I ssh into unit 'lustre-server/0' and I execute 'lctl dl'
    And I ssh into unit 'lustre-server/1' and I execute 'lctl dl'
    Then the ssh output contains 'osd-zfs'
    And the ssh output contains 'MGS'

  @functional @edge
  Scenario: LNet tcp network is configured correctly on the lustre-server units
    Given 'lustre-server' is deployed
    When I ssh into unit 'lustre-server/0' and I execute 'sudo lnetctl net show --net tcp'
    And I ssh into unit 'lustre-server/1' and I execute 'sudo lnetctl net show --net tcp'
    Then the ssh output contains 'net type: tcp' and 'status: up'
    And the ssh output contains 'net type: tcp' and 'status: up'

  @functional @edge
  Scenario: Mount the Lustre filesystem at /lustre on a client
    Given 'lustre-server' is deployed
    And I deploy 'ubuntu' on base 'ubuntu@26.04' from channel 'latest/stable' with constraints 'virt-type=virtual-machine'
    And I deploy 'filesystem-client' on base 'ubuntu@26.04' from channel 'latest/edge'
    And I set 'enable-lustre' for app 'filesystem-client' to 'true'
    And I set 'mountpoint' for app 'filesystem-client' to '/lustre'
    And I integrate 'filesystem-client:filesystem' with 'lustre-server:filesystem'
    And I integrate 'filesystem-client:juju-info' with 'ubuntu:juju-info'
    And I wait for unit 'filesystem-client/0' to exist
    And all agents are 'idle' in model 'lustre'
    And the workload status for unit 'filesystem-client/0' is 'active'
    When I ssh into unit 'ubuntu/0' and I execute 'mount | grep lustre'
    Then the ssh output contains '/lustre'

  @functional @edge
  Scenario: Add an OSS and confirm capacity of the Lustre mount expands
    Given 'lustre-server' is deployed
    And 'filesystem-client' is deployed
    And 'ubuntu' is deployed
    When I ssh into unit 'ubuntu/0' and I execute 'df -k -P /lustre'
    Then the ssh output capacity is between '700000' KB and '1100000' KB
    Given I add '1' units to app 'lustre-server'
    And I add storage 'ost' to unit 'lustre-server/2' from pool 'loop' of size '1G' with '3' instances
    And '3' instances of storage 'ost' are attached to unit 'lustre-server/2'
    And all agents are 'idle' in model 'lustre'
    When I ssh into unit 'ubuntu/0' and I execute 'df -k -P /lustre'
    Then the ssh output capacity is between '1400000' KB and '2200000' KB

  @functional @edge
  Scenario: Stripe count of a file follows the parent directory's stripe setting
    Given 'lustre-server' is deployed
    And 'filesystem-client' is deployed
    And 'ubuntu' is deployed
    When I ssh into unit 'ubuntu/0' and I execute 'sudo lfs setstripe -c 2 /lustre'
    And I ssh into unit 'ubuntu/0' and I execute 'sudo touch /lustre/stripe-test-file'
    And I ssh into unit 'ubuntu/0' and I execute 'lfs getstripe --stripe-count /lustre/stripe-test-file'
    Then the ssh output is '2'
