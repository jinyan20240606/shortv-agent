from google.protobuf.json_format import MessageToDict


def protobuf_to_dict(message):
    return MessageToDict(message, preserving_proto_field_name=True)
