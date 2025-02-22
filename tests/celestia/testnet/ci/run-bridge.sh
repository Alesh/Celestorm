#!/bin/bash

set -euo pipefail

# Name for this node or `bridge-0` if not provided
NODE_ID="${NODE_ID:-0}"
SKIP_AUTH="${SKIP_AUTH:-false}"
NODE_TYPE="${NODE_TYPE:-"bridge"}"
NODE_NAME="$NODE_TYPE-$NODE_ID"
# a private local network
P2P_NETWORK="private"
# a bridge node configuration directory
CONFIG_DIR="$HOME/.celestia-${NODE_TYPE:-"bridge"}-$P2P_NETWORK"
# directory and the files shared with the validator node
CREDENTIALS_DIR="/credentials"
# node credentials
NODE_KEY_FILE="$CREDENTIALS_DIR/$NODE_NAME.key"
NODE_JWT_FILE="$CREDENTIALS_DIR/$NODE_NAME.jwt"
# directory where validator will write the genesis hash
GENESIS_DIR="/genesis"
GENESIS_HASH_FILE="$GENESIS_DIR/genesis_hash"

# Wait for the validator to set up and provision us via shared dir
wait_for_provision() {
  echo "Waiting for the validator node to start"
  while [[ ! ( -e "$GENESIS_HASH_FILE" && -e "$NODE_KEY_FILE" ) ]]; do
    sleep 0.1
  done

  echo "Validator is ready"
}

# Import the test account key shared by the validator
import_shared_key() {
  echo "password" | cel-key import "$NODE_NAME" "$NODE_KEY_FILE" \
    --keyring-backend="test" \
    --p2p.network "$P2P_NETWORK" \
    --node.type $NODE_TYPE
}

add_trusted_genesis() {
  local genesis_hash

  # Read the hash of the genesis block
  genesis_hash="$(cat "$GENESIS_HASH_FILE")"
  # and make it trusted in the node's config
  echo "Trusting a genesis: $genesis_hash"
  sed -i'.bak' "s/TrustedHash = .*/TrustedHash = $genesis_hash/" "$CONFIG_DIR/config.toml"
  if [[ "$NODE_TYPE" == "light" ]] ; then
    sed -i 's/PeerExchange = false/PeerExchange = true/' "$CONFIG_DIR/config.toml"
    sleep 15
    peer="$(cat "$CREDENTIALS_DIR/bridge-0-peer-id.peer")"
    ip="$(getent hosts bridge-0 | awk '{ print $1 }')"
    echo "Added peer to /ip4/$ip/tcp/2121/p2p/$peer"
    dasel put -f "$CONFIG_DIR/config.toml" -t string -v "/ip4/$ip/tcp/2121/p2p/$peer" 'Header.TrustedPeers.[]'
  fi
}

whitelist_localhost_nodes() {
  dasel put -f "$CONFIG_DIR/config.toml" \
    -t json -v '["172.16.0.0/12", "192.168.0.0/16"]' \
    'P2P.IPColocationWhitelist'
}

write_jwt_token() {
  echo "Saving jwt token to $NODE_JWT_FILE"

  celestia $NODE_TYPE auth admin --p2p.network "$P2P_NETWORK" > "$NODE_JWT_FILE"
}

export_peer_id(){

  echo "bridge-0 peer_id" | celestia p2p info | jq -r '.result.id' > "$CREDENTIALS_DIR/$NODE_NAME-peer-id.peer"
}

connect_to_common_bridge() {
  if [[ ! "$NODE_TYPE" == "light" ]] ; then
    sleep 5
    local peer_id=$(celestia p2p info --url 'ws://bridge-0:26658' | jq -r '.result.id')
    echo "Connecting to $peer_id: /dns/bridge-0/tcp/2121"
    celestia p2p connect "$peer_id" "/dns/bridge-0/tcp/2121"
  fi
}

main() {
  # Initialize the bridge node
  celestia $NODE_TYPE init --p2p.network "$P2P_NETWORK"
  # don't allow banning nodes we create in tests by pubsub ip counting
  whitelist_localhost_nodes
  # Wait for a validator
  wait_for_provision
  # Import the key with the coins
  import_shared_key
  # Trust the private blockchain
  add_trusted_genesis
  # Update the JWT token
  write_jwt_token
  # give validator some time to set up
  sleep 4
  # each node without SKIP_AUTH connects to the one with, so that bridges can discover eachother
  if [ ! "$SKIP_AUTH" == "true" ] ; then
    connect_to_common_bridge &
  fi

  if [[ "$NODE_NAME" == "bridge-0" ]] ; then
    (sleep 10 && export_peer_id) &
  fi

  echo -n "$NODE_TYPE" | hexdump -c
  echo "Configuration finished. Running a $NODE_TYPE node..."

  celestia $NODE_TYPE start \
    --rpc.skip-auth="$SKIP_AUTH" \
    --rpc.addr 0.0.0.0 \
    --core.ip validator-0 \
    --keyring.keyname "$NODE_NAME" \
    --p2p.network "$P2P_NETWORK"
}

main
