"use client";

import {
  useEffect,
  useRef,
  useState,
} from "react";

import type {
  ExpertAnatomy,
  ExpertGeometryItem,
  ExpertPoint,
} from "@/components/expert-review-drawer";


type GeometryKind =
  | "POINT"
  | "LINE"
  | "BOX";


interface Tool {
  id: string;
  title: string;

  criterionCode:
    string;

  kind:
    GeometryKind;

  label:
    string;

  unique:
    boolean;
}


interface Props {
  studyId: string;

  anatomy:
    ExpertAnatomy | null;

  geometry:
    ExpertGeometryItem[];

  onChange: (
    value:
      ExpertGeometryItem[],
  ) => void;
}


const TOOLS: Record<
  ExpertAnatomy,
  Tool[]
> = {
  SPINE: [
    {
      id: "th12",
      title: "Th12",
      criterionCode:
        "SPINE_POSITIONING",
      kind: "POINT",
      label: "TH12",
      unique: true,
    },
    {
      id: "iliac-left",
      title: "Гребень L",
      criterionCode:
        "SPINE_POSITIONING",
      kind: "POINT",
      label: "ILIAC_LEFT",
      unique: true,
    },
    {
      id: "iliac-right",
      title: "Гребень R",
      criterionCode:
        "SPINE_POSITIONING",
      kind: "POINT",
      label: "ILIAC_RIGHT",
      unique: true,
    },
    {
      id: "axis",
      title: "Ось",
      criterionCode:
        "SPINE_AXIS",
      kind: "LINE",
      label: "SPINE_AXIS",
      unique: true,
    },
    {
      id: "artifact",
      title: "Артефакт",
      criterionCode:
        "SPINE_ARTIFACTS",
      kind: "BOX",
      label: "ARTIFACT",
      unique: false,
    },
  ],

  HIP: [
    {
      id: "greater",
      title: "Большой вертел",
      criterionCode:
        "HIP_POSITIONING_ROTATION",
      kind: "POINT",
      label:
        "GREATER_TROCHANTER",
      unique: true,
    },
    {
      id: "lesser",
      title: "Малый вертел",
      criterionCode:
        "HIP_POSITIONING_ROTATION",
      kind: "POINT",
      label:
        "LESSER_TROCHANTER",
      unique: true,
    },
    {
      id: "neck",
      title: "Шейка",
      criterionCode:
        "HIP_POSITIONING_ROTATION",
      kind: "POINT",
      label:
        "FEMORAL_NECK",
      unique: true,
    },
    {
      id: "ischial",
      title: "Седалищная кость",
      criterionCode:
        "HIP_POSITIONING_ROTATION",
      kind: "POINT",
      label:
        "ISCHIAL_BONE",
      unique: true,
    },
    {
      id: "roi",
      title: "ROI",
      criterionCode:
        "HIP_ROI",
      kind: "BOX",
      label:
        "ROI_BOUNDARY",
      unique: true,
    },
  ],
};


function clamp(
  value: number,
): number {
  return Math.max(
    0,
    Math.min(
      1,
      value,
    ),
  );
}


function svgPoint(
  point: ExpertPoint,
) {
  return {
    x: point.x * 1000,
    y: point.y * 1000,
  };
}


export function ExpertGeometryCanvas({
  studyId,
  anatomy,
  geometry,
  onChange,
}: Props) {
  const overlayRef =
    useRef<SVGSVGElement | null>(
      null,
    );

  const [
    loaded,
    setLoaded,
  ] = useState(false);

  const [
    failed,
    setFailed,
  ] = useState(false);

  const [
    selectedToolId,
    setSelectedToolId,
  ] = useState<
    string | null
  >(null);

  const [
    draftStart,
    setDraftStart,
  ] = useState<
    ExpertPoint | null
  >(null);


  const tools =
    anatomy
      ? TOOLS[anatomy]
      : [];

  const selectedTool =
    tools.find(
      (item) =>
        item.id
        === selectedToolId,
    ) ?? null;


  useEffect(
    () => {
      setSelectedToolId(
        null,
      );

      setDraftStart(
        null,
      );
    },
    [
      anatomy,
    ],
  );


  function normalizedPoint(
    event:
      React.PointerEvent<
        SVGSVGElement
      >,
  ): ExpertPoint | null {
    const element =
      overlayRef.current;

    if (!element) {
      return null;
    }

    const rect =
      element
        .getBoundingClientRect();

    if (
      rect.width <= 0
      || rect.height <= 0
    ) {
      return null;
    }

    return {
      x: clamp(
        (
          event.clientX
          - rect.left
        ) / rect.width,
      ),

      y: clamp(
        (
          event.clientY
          - rect.top
        ) / rect.height,
      ),
    };
  }


  function appendGeometry(
    item:
      ExpertGeometryItem,
    unique: boolean,
  ) {
    const base =
      unique
        ? geometry.filter(
            (current) =>
              !(
                current
                  .criterionCode
                  === item
                    .criterionCode
                && current.label
                  === item.label
              ),
          )
        : geometry;

    onChange([
      ...base,
      item,
    ]);
  }


  function onPointerDown(
    event:
      React.PointerEvent<
        SVGSVGElement
      >,
  ) {
    if (!selectedTool) {
      return;
    }

    const point =
      normalizedPoint(
        event,
      );

    if (!point) {
      return;
    }

    if (
      selectedTool.kind
      === "POINT"
    ) {
      appendGeometry(
        {
          criterionCode:
            selectedTool
              .criterionCode,

          kind:
            selectedTool.kind,

          label:
            selectedTool.label,

          points: [
            point,
          ],
        },

        selectedTool.unique,
      );

      return;
    }

    if (!draftStart) {
      setDraftStart(
        point,
      );

      return;
    }

    appendGeometry(
      {
        criterionCode:
          selectedTool
            .criterionCode,

        kind:
          selectedTool.kind,

        label:
          selectedTool.label,

        points: [
          draftStart,
          point,
        ],
      },

      selectedTool.unique,
    );

    setDraftStart(
      null,
    );
  }


  function undo() {
    if (draftStart) {
      setDraftStart(
        null,
      );

      return;
    }

    onChange(
      geometry.slice(
        0,
        -1,
      ),
    );
  }


  function clearCurrentAnatomy() {
    const currentCodes =
      new Set(
        tools.map(
          (tool) =>
            tool.criterionCode,
        ),
      );

    onChange(
      geometry.filter(
        (item) =>
          !currentCodes.has(
            item.criterionCode,
          ),
      ),
    );

    setDraftStart(
      null,
    );
  }


  return (
    <div
      className={
        "expert-geometry-shell"
      }
    >
      <div
        className={
          "expert-geometry-toolbar"
        }
      >
        <div>
          <strong>
            Геометрическая разметка
          </strong>

          <span>
            Выберите инструмент
            и отметьте ориентиры.
          </span>
        </div>

        <div
          className={
            "expert-geometry-tools"
          }
        >
          {tools.map(
            (tool) => (
              <button
                key={tool.id}
                type="button"
                className={
                  selectedToolId
                    === tool.id
                    ? (
                        "expert-geometry-tool "
                        + "active"
                      )
                    : (
                        "expert-geometry-tool"
                      )
                }
                onClick={() => {
                  setSelectedToolId(
                    (
                      current,
                    ) =>
                      current
                        === tool.id
                        ? null
                        : tool.id,
                  );

                  setDraftStart(
                    null,
                  );
                }}
              >
                {tool.title}
              </button>
            ),
          )}
        </div>
      </div>


      <div
        className={
          "expert-image-stage"
        }
      >
        {!failed && (
          <div
            className={
              "expert-image-canvas"
            }
          >
            <img
              className={
                loaded
                  ? (
                      "expert-image "
                      + "loaded"
                    )
                  : "expert-image"
              }
              src={
                `/api/backend/studies/${studyId}/preview`
              }
              alt={
                "DXA исследование"
              }
              onLoad={() =>
                setLoaded(
                  true,
                )
              }
              onError={() =>
                setFailed(
                  true,
                )
              }
            />

            {loaded && (
              <svg
                ref={overlayRef}
                className={
                  selectedTool
                    ? (
                        "expert-svg-overlay "
                        + "interactive"
                      )
                    : (
                        "expert-svg-overlay"
                      )
                }
                viewBox={
                  "0 0 1000 1000"
                }
                preserveAspectRatio={
                  "none"
                }
                onPointerDown={
                  onPointerDown
                }
              >
                {geometry.map(
                  (
                    item,
                    index,
                  ) => {
                    const first =
                      svgPoint(
                        item.points[0],
                      );

                    if (
                      item.kind
                      === "POINT"
                    ) {
                      return (
                        <g
                          key={
                            `${item.label}-${index}`
                          }
                        >
                          <circle
                            cx={first.x}
                            cy={first.y}
                            r="11"
                            className={
                              "expert-mark-point"
                            }
                          />

                          <text
                            x={
                              first.x
                              + 16
                            }
                            y={
                              first.y
                              - 12
                            }
                            className={
                              "expert-mark-label"
                            }
                          >
                            {
                              item.label
                            }
                          </text>
                        </g>
                      );
                    }

                    const second =
                      svgPoint(
                        item.points[1],
                      );

                    if (
                      item.kind
                      === "LINE"
                    ) {
                      return (
                        <line
                          key={
                            `${item.label}-${index}`
                          }
                          x1={first.x}
                          y1={first.y}
                          x2={second.x}
                          y2={second.y}
                          className={
                            "expert-mark-line"
                          }
                        />
                      );
                    }

                    if (
                      item.kind
                      === "BOX"
                    ) {
                      const x =
                        Math.min(
                          first.x,
                          second.x,
                        );

                      const y =
                        Math.min(
                          first.y,
                          second.y,
                        );

                      const width =
                        Math.abs(
                          second.x
                          - first.x,
                        );

                      const height =
                        Math.abs(
                          second.y
                          - first.y,
                        );

                      return (
                        <rect
                          key={
                            `${item.label}-${index}`
                          }
                          x={x}
                          y={y}
                          width={width}
                          height={height}
                          className={
                            "expert-mark-box"
                          }
                        />
                      );
                    }

                    return null;
                  },
                )}

                {draftStart && (
                  <circle
                    cx={
                      draftStart.x
                      * 1000
                    }
                    cy={
                      draftStart.y
                      * 1000
                    }
                    r="12"
                    className={
                      "expert-mark-draft"
                    }
                  />
                )}
              </svg>
            )}
          </div>
        )}

        {!loaded
          && !failed
          && (
            <div
              className={
                "viewer-placeholder"
              }
            >
              <strong>
                Загружаем DICOM
              </strong>

              <span>
                Формируем безопасный
                preview…
              </span>
            </div>
          )}

        {failed && (
          <div
            className={
              "viewer-placeholder"
            }
          >
            <strong>
              Preview недоступен
            </strong>

            <span>
              Невозможно отобразить
              исследование.
            </span>
          </div>
        )}
      </div>


      <div
        className={
          "expert-geometry-footer"
        }
      >
        <span>
          Объектов:
          {" "}
          {geometry.length}
        </span>

        <div>
          <button
            type="button"
            className={
              "expert-geometry-action"
            }
            disabled={
              geometry.length === 0
              && !draftStart
            }
            onClick={undo}
          >
            ↶ Отменить
          </button>

          <button
            type="button"
            className={
              "expert-geometry-action"
            }
            disabled={
              geometry.length === 0
            }
            onClick={
              clearCurrentAnatomy
            }
          >
            Очистить
          </button>
        </div>
      </div>
    </div>
  );
}
