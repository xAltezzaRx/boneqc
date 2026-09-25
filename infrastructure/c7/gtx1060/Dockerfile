FROM boneqc-c7-final:runtime-v1

USER root

RUN python -m pip install \
    --no-cache-dir \
    --force-reinstall \
    --index-url https://download.pytorch.org/whl/cu126 \
    torch==2.14.0 \
    torchvision==0.29.0

LABEL org.boneqc.runtime.role="gtx1060-fallback"
LABEL org.boneqc.runtime.base="boneqc-c7-final:runtime-v1"
LABEL org.boneqc.runtime.cuda-compat="cu126"
