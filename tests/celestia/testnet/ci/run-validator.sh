#!/bin/bash

set -euo pipefail

CELESTIA_HOME="root"
NODE_ID="${NODE_ID:-0}"
BRIDGE_COUNT="${BRIDGE_COUNT:-1}"
VALIDATOR_COUNT="${VALIDATOR_COUNT:-0}"
LIGHT_COUNT="${LIGHT_COUNT:-0}"
P2P_NETWORK="private"
CONFIG_DIR="$CELESTIA_HOME/.celestia-app"
NODE_NAME="validator-$NODE_ID"
BRIDGE_COINS="200000000000000utia"
VALIDATOR_COINS="1000000000000000utia"
CREDENTIALS_DIR="/credentials"
GENESIS_DIR="/genesis"
GENESIS_HASH_FILE="$GENESIS_DIR/genesis_hash"
NODE_KEY_FILE="$CREDENTIALS_DIR/$NODE_NAME.key"
TIME_SLEEP=40


node_address() {
  local node_name="$1"
  local node_address
  node_address=$(celestia-appd keys show "$node_name" -a --keyring-backend="test")
  echo "$node_address"
}

wait_for_block() {
  local block_num="$1"
  local block_hash=""

  while [[ -z "$block_hash" ]]; do
    block_hash="$(celestia-appd query block "$block_num" 2>/dev/null | jq '.block_id.hash' || echo)"
    sleep 0.1
  done

  echo "$block_hash"
}

provision_bridge_nodes() {
  local genesis_hash
  local last_node_idx=$((BRIDGE_COUNT - 1))

  genesis_hash=$(wait_for_block 1)

  echo "Saving a genesis hash to $GENESIS_HASH_FILE"
  echo "$genesis_hash" > "$GENESIS_HASH_FILE"

  for node_idx in $(seq 0 "$last_node_idx"); do
    local bridge_name="bridge-$node_idx"
    local key_file="$CREDENTIALS_DIR/$bridge_name.key"
    local plaintext_key_file="$CREDENTIALS_DIR/$bridge_name.plaintext-key"
    local addr_file="$CREDENTIALS_DIR/$bridge_name.addr"

    if [ ! -e "$key_file" ]; then
      echo "Creating a new keys for the $bridge_name"

      celestia-appd keys add "$bridge_name" --keyring-backend "test"
      echo "password" | celestia-appd keys export "$bridge_name" 2> "$key_file.lock"
      echo y | celestia-appd keys export "$bridge_name" --unsafe --unarmored-hex 2> "${plaintext_key_file}"
      mv "$key_file.lock" "$key_file"
      node_address "$bridge_name" > "$addr_file"
    else
      echo "password" | celestia-appd keys import "$bridge_name" "$key_file" \
        --keyring-backend="test"
    fi
  done

  local start_block=2

  for node_idx in $(seq 0 "$last_node_idx"); do
    wait_for_block $((start_block + node_idx))
    local bridge_name="bridge-$node_idx"
    local bridge_address

    bridge_address=$(node_address "$bridge_name")
    echo "Transfering $BRIDGE_COINS coins from "$NODE_NAME" to the $bridge_name"

    echo "y" | celestia-appd tx bank send \
      "$NODE_NAME" \
      "$bridge_address" \
      "$BRIDGE_COINS" \
      --fees 21000utia
  done

  echo "Provisioning finished."
}

provision_validator_nodes(){
  local genesis_hash
  local last_node_idx=$((VALIDATOR_COUNT))

  genesis_hash=$(wait_for_block 1)
  echo "Saving a genesis hash to $GENESIS_HASH_FILE"
  echo "$genesis_hash" > "$GENESIS_HASH_FILE"

  for node_idx in $(seq 1 "$last_node_idx"); do
    local validator_name="validator-$node_idx"
    local key_file="$CREDENTIALS_DIR/$validator_name.key"
    echo "password" | celestia-appd keys import "$validator_name" "$key_file" \
        --keyring-backend="test"
  done

  local start_block=$((2 + BRIDGE_COUNT))

  for node_idx in $(seq 1 "$last_node_idx"); do
    wait_for_block $((start_block + node_idx - 1))
    local validator_name="validator-$node_idx"
    local validator_address

    validator_address=$(node_address "$validator_name")
    echo "Transfering $BRIDGE_COINS coins from "$NODE_NAME" to the $validator_name, $validator_address"

    echo "y" | celestia-appd tx bank send \
      "$NODE_NAME" \
      "$validator_address" \
      "2000000000000utia" \
      --fees 21000utia
  done
}

provision_light_nodes(){
  local genesis_hash
  local last_node_idx=$((LIGHT_COUNT-1))

  genesis_hash=$(wait_for_block 1)
  echo "Saving a genesis hash to $GENESIS_HASH_FILE"
  echo "$genesis_hash" > "$GENESIS_HASH_FILE"

  for node_idx in $(seq 0 "$last_node_idx"); do
    local light_name="light-$node_idx"
    local key_file="$CREDENTIALS_DIR/$light_name.key"
    local plaintext_key_file="$CREDENTIALS_DIR/$light_name.plaintext-key"
    local addr_file="$CREDENTIALS_DIR/$light_name.addr"

    if [ ! -e "$key_file" ]; then
      echo "Creating a new keys for the $light_name"
      celestia-appd keys add "$light_name" --keyring-backend "test"
      echo "password" | celestia-appd keys export "$light_name" 2> "$key_file.lock"
      echo y | celestia-appd keys export "$light_name" --unsafe --unarmored-hex 2> "${plaintext_key_file}"
      mv "$key_file.lock" "$key_file"
      node_address "$light_name" > "$addr_file"
    else
      echo "password" | celestia-appd keys import "$light_name" "$key_file" \
        --keyring-backend="test"
    fi
  done

  local start_block=$((2+BRIDGE_COUNT+VALIDATOR_COUNT))

  for node_idx in $(seq 0 "$last_node_idx"); do
    wait_for_block $((start_block + node_idx))
    local light_name="light-$node_idx"
    local light_address

    light_address=$(node_address "$light_name")
    echo "Transfering $BRIDGE_COINS coins from "$NODE_NAME" to the $light_name"

    echo "y" | celestia-appd tx bank send \
      "$NODE_NAME" \
      "$light_address" \
      "$BRIDGE_COINS" \
      --fees 21000utia
  done


}

setup_private_validator() {
  local validator_addr
  local key_file="$CREDENTIALS_DIR/"$NODE_NAME".key"
  local plaintext_key_file="$CREDENTIALS_DIR/"$NODE_NAME".plaintext-key"
  local addr_file="$CREDENTIALS_DIR/"$NODE_NAME"-conv.addr"
  local addr_before_conv_file="$CREDENTIALS_DIR/"$NODE_NAME".addr"

  celestia-appd init "$P2P_NETWORK" --chain-id "$P2P_NETWORK"
  if [ ! -e "$key_file" ]; then
    echo "Creating a new keys for the $NODE_NAME"

    celestia-appd keys add "$NODE_NAME" --keyring-backend="test"
    local validator_addr
    validator_addr="$(celestia-appd keys show "$NODE_NAME" -a --keyring-backend="test")"
    echo "password" | celestia-appd keys export "$NODE_NAME" 2> "$key_file.lock"
    echo y | celestia-appd keys export "$NODE_NAME" --unsafe --unarmored-hex 2> "${plaintext_key_file}"
    mv "$key_file.lock" "$key_file"
    node_address "$NODE_NAME" > "$addr_before_conv_file"
    celestia-appd addr-conversion "$validator_addr" > "$addr_file"
  else
    echo "Importing keys for the $NODE_NAME"

    echo "password" | celestia-appd keys import "$NODE_NAME" "$key_file" \
      --keyring-backend="test"
  fi
  validator_addr="$(celestia-appd keys show "$NODE_NAME" -a --keyring-backend="test")"
  celestia-appd add-genesis-account "$validator_addr" "$VALIDATOR_COINS"
  celestia-appd gentx "$NODE_NAME" 5000000000utia \
    --fees 500utia \
    --keyring-backend="test" \
    --chain-id "$P2P_NETWORK"
  celestia-appd collect-gentxs

  sed -i'.bak' 's|"tcp://127.0.0.1:26657"|"tcp://0.0.0.0:26657"|g' "$CONFIG_DIR/config/config.toml"
  sed -i'.bak' 's|indexer = .*|indexer = "kv"|g' "$CONFIG_DIR/config/config.toml"
}

main() {
  setup_private_validator
  if [ "$NODE_NAME" = "validator-0" ]; then
    provision_validator_nodes &
    provision_bridge_nodes &
    provision_light_nodes &
  fi
  celestia-appd start --api.enable --grpc.enable --force-no-bbr &
  sleep $TIME_SLEEP
  if [ "$NODE_NAME" != "validator-0" ]; then
    echo "Configuration finished. Running a $NODE_NAME node..."

    HOST="validator-0"
  else
    echo "Configuration finished. Running a $NODE_NAME..."

    HOST="0.0.0.0"
  fi
  celestia-appd tx staking create-validator \
    --amount=1000000utia \
    --pubkey=$(celestia-appd tendermint show-validator) \
    --moniker="moniker-$NODE_NAME" \
    --node="tcp://$HOST:26657" \
    --chain-id=$P2P_NETWORK \
    --commission-rate=0.1 \
    --commission-max-rate=0.2 \
    --commission-max-change-rate=0.01 \
    --min-self-delegation=1000000 \
    --from=$NODE_NAME \
    --keyring-backend=test \
    --fees=21000utia \
    --gas=220000 \
    --yes
  while true; do
    sleep 0.1
  done
}

main