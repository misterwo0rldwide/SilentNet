/*
 * mac_find.c - Handles searching for mac address
 *
 *              Omer Kfir (C)
 */

#include "mac_find.h"
#include "headers.h"

// Function to find consistent mac address
void get_mac_address(char *mac_buf) {
  struct net_device *dev;
  struct net_device *chosen_dev = NULL;
  char lowest_mac[ETH_ALEN] = {0xff, 0xff, 0xff, 0xff, 0xff, 0xff};

  /*
   * When searching for mac address iterating through netdevices
   * Does not ensure finding the same mac as netdevices list changes
   * Therefore we will find the lowest valued mac address
   */

  rcu_read_lock();
  for_each_netdev(&init_net, dev) {     // Iterate through netdevices list
    if (!(dev->flags & IFF_LOOPBACK)) { // Ensure netdevice isn't a loopback
      int i;
      for (i = 0; i < ETH_ALEN;
           i++) { // Iterates through the octats, Finds min octat and replaces
        if (dev->dev_addr[i] < lowest_mac[i]) {
          memcpy(lowest_mac, dev->dev_addr, ETH_ALEN);
          chosen_dev = dev;
          break;
        } else if (dev->dev_addr[i] > lowest_mac[i]) {
          break;
        }
      }
    }
  }

  if (chosen_dev) {
    // Format MAC address as string
    snprintf(mac_buf, 18, "%02x:%02x:%02x:%02x:%02x:%02x", lowest_mac[0],
             lowest_mac[1], lowest_mac[2], lowest_mac[3], lowest_mac[4],
             lowest_mac[5]);
  } else {
    // In case no suitable interface is found
    strncpy(mac_buf, "00:00:00:00:00:00", 17);
  }
  rcu_read_unlock();
}