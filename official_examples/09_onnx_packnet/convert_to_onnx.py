#!/usr/bin/env python3
import torch
import onnx
import numpy as np
import argparse
import onnx_graphsurgeon as gs
from post_processing import *
from monodepth.models.networks.PackNet01 import PackNet01


def post_process_packnet(model_file, opset=11):
    """
    Use ONNX graph surgeon to replace upsample and instance normalization nodes. Refer to post_processing.py for details.
    Args:
        model_file : Path to ONNX file
    """
    # Load the packnet graph
    graph = gs.import_onnx(onnx.load(model_file))

    if opset==11:
        graph = process_pad_nodes(graph)

    # Replace the subgraph of upsample with a single node with input and scale factor.
    graph = process_upsample_nodes(graph, opset)

    # Convert the group normalization subgraph into a single plugin node.
    graph = process_groupnorm_nodes(graph)

    # Remove unused nodes, and topologically sort the graph.
    graph.cleanup().toposort()

    # Export the onnx graph from graphsurgeon
    onnx.save_model(gs.export_onnx(graph), model_file)

    print("Saving the ONNX model to {}".format(model_file))


def build_packnet(model_file, args):
    """
    Construct the packnet network and export it to ONNX
    """
    input_pyt = torch.randn((1, 3, 640, 192), requires_grad=False)

    # Build the model
    model_pyt = PackNet01(version='1A')

    # Convert the model into ONNX
    torch.onnx.export(model_pyt, input_pyt, model_file, verbose=args.verbose, opset_version=args.opset)


def main():
    parser = argparse.ArgumentParser(description="Exports PackNet01 to ONNX, and post-processes it to insert TensorRT plugins")
    parser.add_argument("-o", "--output", help="Path to save the generated ONNX model", default="model.onnx")
    parser.add_argument("-op", "--opset", type=int, help="ONNX opset to use", default=11)
    parser.add_argument("-v", "--verbose", action='store_true', help="Flag to enable verbose logging for torch.onnx.export")
    args=parser.parse_args()

    # Construct the packnet graph and generate the onnx graph
    build_packnet(args.output, args)

    # Perform post processing on Instance Normalization and upsampling nodes and create a new ONNX graph
    post_process_packnet(args.output, args.opset)


if __name__ == '__main__':
    main()
