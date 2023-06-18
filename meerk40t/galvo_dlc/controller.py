"""
Galvo Controller

Takes low level dlc galvo commands and converts them into lists and shorts commands to send to the hardware controller.
"""

import struct
import time
from copy import copy

from meerk40t.balormk.mock_connection import MockConnection
from meerk40t.balormk.usb_connection import USBConnection
from meerk40t.fill.fills import Wobble

DRIVER_STATE_RAPID = 0
DRIVER_STATE_LIGHT = 1
DRIVER_STATE_PROGRAM = 2
DRIVER_STATE_RAW = 3
nop = [0x81, 0x80, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
empty = bytearray(nop * 0x100)


lSetLaserMode = 0x8001
lSetLaserActive = 0x8002
lLaserOn = 0x8003
lLaserOff = 0x8004
lSetLaserPower = 0x8006
lSetLaserTimeBase = 0x8007
lSetLaserPWMPara = 0x8008
lSetLaserStandByPara = 0x8009
lSetLaserQSwitchDelay = 0x800A
lSetRedDiodeGuide = 0x800B
lSetLaserSerialCmd = 0x800C
lSetLaserParaByUart = 0x800D
lSetLaserOnWithTime = 0x800F
lLaserDirectControl = 0x8010
lSetLaserOnTimeCount = 0x8011
lLaserOnWithFixTime = 0x8012
lSetLaserPWMCountClock = 0x8013
lSetLaserOnDelayCorPara = 0x8014
lSetLaserPWMInverse = 0x8015
lSetLaserOnLagTime = 0x8016
lSetLaserPowerVariable = 0x8017
lSetJumpSpeed = 0x8021
lSetMarkSpeed = 0x8022
lSetScanDelay = 0x8023
lSetJumpDelayWorkMode = 0x8024
lSelectScannerOutputMode = 0x8026
lAdjustScanner2DPos = 0x8027
lSetVariableFloat = 0x8028
lSetVariableInt = 0x8029
lSetVariableFloatToParam = 0x802A
lSetVariableIntToParam = 0x802B
lSetWobbleCurveParamter = 0x802C
lJumpAbs2D = 0x8041
lJumpRel2D = 0x8042
lJumpAbs2DWithPosDetect = 0x8043
lHardJumpAbs2D = 0x8044
lTimedJumpAbs2D = 0x8046
lMarkAbs2D = 0x8061
lMarkRel2DWithIOCheck = 0x8062
lMarkAbs2DWithPOD = 0x8063
lWritePODCtrlData = 0x8064
lMarkAbs2DWithPosDetect = 0x8065
lSendPosCoorData = 0x8066
lSetArcCenter = 0x8067
lMarkArcAbs2D = 0x8068
lTimedMarkAbs2D = 0x8069
lMarkAbs2DWithDashDot = 0x806B
lStartPODMark = 0x806C
lWriteDottedLineApCtrlData = 0x806D
lMarkAbs2DWithDottedLine = 0x806E
lSetDottedLinePosDealy = 0x806F
lSetEndOfList = 0x8081
lListDelay = 0x8082
lListNop = 0x8083
lListAutoChange = 0x8084
lListPause = 0x8085
lListJumpToSpecifiedIndex = 0x8086
lListJumpToIndexWithCompareCond = 0x8087
lListRepeat = 0x8088
lListUntil = 0x8089
lListIfIOCond = 0x808A
lResetMatrix = 0x80B2
lAutoSelectListMatirx = 0x80B3
lSelect2DCorFile = 0x80C1
lSelectZCorrection = 0x80C2
lSelectDynZCorrection = 0x80C3
lSelectHRC2DCorFile = 0x80C4
lSetFreq10usSyn = 0x80D1
lSetScannerProtocal = 0x80D2
lSetMinJumpLength = 0x80D3
lResetCounter = 0x80D4
lSetCounter = 0x80D5
lStartMarkTimer = 0x80D6
lStopMarkTimer = 0x80D7
lSetCurveMarkPara = 0x80D8
lSetOutputPort = 0x80D9
lWaitForInputPort = 0x80DA
lSetInputPort0Mode = 0x80DB
lSetInputPortMode = 0x80DB
lClearInputPort0State = 0x80DC
lClearInputPortState = 0x80DC
lStartSaveScannerPosition = 0x80DE
lSetInputPortIn8_9Mode = 0x80DF
lClearInputPortIn8_9State = 0x80E0
lSetPositionDetectPara = 0x80E1
lSetListIndexObject = 0x80E2
lExecuteListWithIOCheck = 0x80E3
lStartSerialComWithCCDCmd = 0x80E4
lSetOutputPWMPara = 0x80E6
lStartFlyWaitWithSerialCom = 0x80E7
lStartLaserMonitorProcess = 0x80E8
lSetOutputBitPort = 0x80E9
lSetSkyWritingPara = 0x80EA
lSelectListMatrix = 0x80EB
lSetScannerTrackError = 0x80EC
lSetMarkStepPitchMode = 0x80ED
lResetFlyWaitLatchedPosBuf = 0x80EE
lSetFlyWaitPositionIndex = 0x80EF
lSetMinIntervalTriggerCond = 0x80F0
lSetOutputPortWithMask = 0x80F1
lSetInputPortFilterPara = 0x80F2
lSetMarkTimeIndex = 0x80F3
lChooseScannerRetStatusCode = 0x80F4
lSetExtCurveMarkPara = 0x80F5
lMarkPixelLinePara1 = 0x8100
lMarkPixelLinePara2 = 0x8101
lMarkPixelLinePara3 = 0x8102
lMarkPixelLine4 = 0x8103
lSetFlyEnable = 0x8110
lResetFlyDistance = 0x8111
lFlyWaitDistance = 0x8112
lResetFlyCorrectionValue = 0x8114
lFlyWaitXYPosition = 0x8115
lFlyWaitCameraPositioning = 0x8116
lSetEncoderPara = 0x8117
lSetFlyX = 0x8118
lSetFlyY = 0x8119
lSetFlyRot = 0x811A
lSetSimulatorEncoder = 0x811B
lSetFlyFactorRatio = 0x811C
lEnableFlyCorrection = 0x811D
lLaserCtrlWithEncoderPosition = 0x811E
lFlyWaitRelDistance = 0x811F
lMarkAbs3D = 0x8120
lJumpAbs3D = 0x8121
lMarkAbs3DWithPosDetect = 0x8122
lJumpAbs3DWithPosDetect = 0x8123
lResetScanner = 0x8151
lReadListFile = 0x8152
lSetListLoop = 0x8153
lDoListLoop = 0x8154
lCheckIOStatus = 0x8155
lStepperInit = 0x8181
lStepperInit2 = 0x8187
lStepperInit3 = 0x8188
lStepperSingleAxisMove = 0x8182
lStepperMultiAxisMove = 0x8183
lStepperSingleAxisOrigin = 0x8184
lStepperMultiAxisOrigin = 0x8185
lStepperAxisReset = 0x8186
lWritePCOApCtrlData = 0x81B1
lSetPSOPositionSource = 0x81D1
lSetPSOPulseWidth = 0x81D2
lSetPSOFunctionControl = 0x81D3
lResetPSO = 0x81D3
lStartPSO = 0x81D3
lStopPSO = 0x81D3
lSetPSODistanceCounter = 0x81D4
lSetPSOMaxInterval = 0x81D5
lEnableRedDiode = 0x8200

cLoad2DCorFile = "Unknown"
cSetJumpLookUpTable = "Unknown"
cSetLaserDelay = "Unknown"
cConfigList = 0x0001
cLoadList = 0x0002
cExecuteList = 0x0003
cStopExecution = 0x0004
cPauseList = 0x0005
cRestartList = 0x0006
cListAutoChange = 0x0007
cCloseList = 0x0008
cResetList = 0x0009
cSetListMode = 0x000a
cForceSendList = 0x000c
cSetListPauseStatus = 0x000d
cSetLaserMode = 0x0021
cSetLaserActive = 0x0022
cLaserOn = 0x0023
cLaserOff = 0x0024
cSetLaserPower = 0x0026
cSetLaserTimeBase = 0x0027
cSetLaserFreq = 0x0028
cSetLaserPWMPara = 0x0028
cSetLaserStandByPara = 0x0029
cSetLaserQSwitchDelay = 0x002a
cSetRedDiodeGuide = 0x002b
cSetLaserSerialCmd = 0x002c
cSetLaserParaByUart = 0x002d
cLaserDirectControl = 0x0032
cSetLaserOnTimeCount = 0x0033
cLaserOnWithFixTime = 0x0034
cSetLaserPWMCountClock = 0x0035
cSetLaserOnDelayCorPara = 0x0036
cSetLaserOnLagTime = 0x0037
cSetLaserPWMInverse = 0x0038
cSetAutoLaserCtrlWithSpeed = 0x0039
cSetLaserPWMFPKPara = 0x003a
cSetLaseAnalogFPKPara = 0x003b
cSelect2DCorFile = 0x0044
cLoadZCorFile = 0x0045
cSelectZCorrection = 0x0048
cLoadZCorFile2 = 0x0049
cSetXYParam = 0x0081
cSystemReset = 0x0082
cSetCalibrationFactor = 0x0083
cSetScannerProtocal = 0x0084
cSetMinJumpLength = 0x0085
cResetCounter = 0x0086
cSetCounter = 0x0087
cSetOutputPort = 0x0089
cWriteBoardMemory = 0x008a
cSetInputPort0Mode = 0x008b
cSetInputPortMode = 0x008b
cClearInputPort0State = 0x008c
cWriteBoardIdentifier = 0x008d
cResetScannerPosition = 0x008e
cEnableDynamicFocus = 0x008f
cSetInputPortIn8_9Mode = 0x0090
cSetInputPortMode2 = 0x0090
cClearInputPortIn8_9State = 0x0091
cClearInputPortState = 0x0091
cSetPositionDetectPara = 0x0092
cSetInputPortWorkMode = 0x0093
cSetOutputPWMPara = 0x0094
cSetEncoderPara = 0x00a1
cSetFlyX = 0x00a2
cSetFlyY = 0x00a3
cSetFlyTrackingError = 0x00a4
cSetFlyRot = 0x00a5
cResetEncoderCount = 0x00a7
cSetSimulatorEncoder = 0x00a9
cResetFlyDistance = 0x00aa
cResetFlyCorrectionValue = 0x00ac
cStartFlyVelocityMonitorProcess = 0x00ad
cStartSaveListFile = 0x00d1
cStopSaveListFile = 0x00d2
cStartSaveListMain = 0x00d3
cStopSaveListMain = 0x00d4
cSaveCorFile = 0x00d5
cEnableListSave = 0x00d6
cSetMatrix = 0x00f1
cSetListMatrix = 0x00f2
cSetJumpSpeed = 0x0101
cSetMarkSpeed = 0x0102
cSetScanDelay = 0x0103
cSetJumpDelayWorkMode = 0x0104
cSelectScannerOutputMode = 0x0106
cSetScannerXYLagTime = 0x0107
cSetScannerRandomJitter = 0x0108
cSetWobbleCurveParamter = 0x0109
cLoadDynZCorFile = 0x0145
cLoadHRC2DCorFile = 0x0147
cSelectHRC2DCorFile = 0x0150
cLoadXYEncoderCorFile = 0x0151
cLoadMultiLayer2DCorFile = 0x0154
cEnableMultiLayer2DCorFile = 0x0157
cLoadMultiLayerZCorFile = 0x0158
cLoadMultiLayerCorAssistFile = 0x015b
cSetPolygonLaserDelay = 0x0172
cSetPolygonLaserOnTime = 0x0174
cStartPolygonMark = 0x0175
cStopPolygonMark = 0x0176
cSetLaserAdjustPara = 0x0177
cSetLaserEnergyFollowPara = 0x0178
cSetExtOutputPort = 0x0179
cWriteEncryptIDInfo = 0x017a
cSetOutputBitPort = 0x017b
cStartUSBMonitorProcess = 0x017c
cSendHeartBeatCmd = 0x017d
cSetSkyWritingPara = 0x017e
cGet3DPrintAnalogOutput = 0x017f
cSet3DPrintAnalogOutput = 0x017f
cSet3DPrintPWMOutput = 0x017f
cSet3DPrintSerialCmd = 0x017f
cStepperOutputCtrlSignal = 0x017f
cSetPolygonArcRadius = 0x0181
cStartLaserStatusMonitor = 0x0182
cSetScannerTrackError = 0x0183
cSetMarkStepPitchMode = 0x0184
cStartMainLoopIOCheckProcess = 0x0185
cSetStopMarkIOWorkPara = 0x0186
cSetPulseOutput = 0x0187
cSetMinIntervalTriggerCond = 0x0188
cSetDynFieldDistribution = 0x0189
cSetLaserIOSynOutput = 0x018a
cSetOutputPortWithMask = 0x018b
cStartScannerStatusMonitor = 0x018c
cSetInputPortFilterPara = 0x018d
cSetVariableFloat = 0x018e
cSetVariableInt = 0x018f
cSetBoardSerialNo = 0x0190
cSetOutputPortAutoSave = 0x0191
cStartInputportTriggerMonitor = 0x0192
cChooseScannerRetStatusCode = 0x0193
cStepperInit = 0x01b1
cStepperSingleAxisMove = 0x01b2
cStepperMultiAxisMove = 0x01b3
cStepperSingleAxisOrigin = 0x01b4
cStepperMultiAxisOrigin = 0x01b5
cStepperAxisReset = 0x01b6
cStepperEnableAxisLimitSwitch = 0x01b7
cStepperEnableHandWheel = 0x01b8
cStepperAxisVelocityMode = 0x01b9
cStepperInit2 = 0x01ba
cStepperInit3 = 0x01bb
cStepperPositionClear = 0x01bc
cStepperPulseWidth = 0x01bd
cSetPCOEnable = 0x01e1
cSetPCOZIndexMode = 0x01e2
cSetPCOWorkPara = 0x01e3
cSetPCOWorkPara1 = 0x01e3
cSetPCOWorkPara2 = 0x01e4
cSetPCOPulseInterval = 0x01e5
cSetPCOPulseIntervalBase = 0x01e5
cSetPCOAPWid = 0x01e6
cSetPCOAPMode = 0x01e7
cSetPCOSingleAxisMove = 0x01e8
cSetPCOZIndexDelay = 0x01e9
cSetPCOWorkMode = 0x01ec
cSetPCOZCountEveryCycle = 0x01ed
cSetPCOExtTriggerEnable = 0x01f0
cSetPCOExtPulseMode = 0x01f1
cSetPCOExtPulseFreq = 0x01f3
cSetPCOSubDivisionPulseCount = 0x01f4
cSetPCOAxisFollowPara = 0x01f5
cSetPCOXAxisMove = 0x01f6
cSetPCOJitterTime = 0x01f9
cSetPSOPositionSource = 0x0231
cSetPSOPulseWidth = 0x0232
cResetPSO = 0x0233
cSetPSOFunctionControl = 0x0233
cStartPSO = 0x0233
cStopPSO = 0x0233
cSetPSODistanceCounter = 0x0234
cSetPSOMaxInterval = 0x0235
cSetPSOFreqPara = 0x0236
cSetPolyScannerSpeed = 0x0261
cStartPolyScannerRun = 0x0262
cStopPolyScannerRun = 0x0263
cClearPolyScannerError = 0x0264
cSetPolyScannerSOSDelay = 0x0266
cSetPolyScannerFixedSOSWork = 0x0268
cSetPolyScannerSOSCorValue = 0x0269
cSetPolyScannerYCorPara = 0x026a
cSetPolyScannerPWMPara = 0x026c
cSendDspFirmware = 0x0291
cSendFPGAFirmware = 0x0292
cStartFirmwareUpdate = 0x0294


list_command_lookup = {
    0x8001: "lSetLaserMode",
    0x8002: "lSetLaserActive",
    0x8003: "lLaserOn",
    0x8004: "lLaserOff",
    0x8006: "lSetLaserPower",
    0x8007: "lSetLaserTimeBase",
    0x8008: "lSetLaserPWMPara",
    0x8009: "lSetLaserStandByPara",
    0x800A: "lSetLaserQSwitchDelay",
    0x800B: "lSetRedDiodeGuide",
    0x800C: "lSetLaserSerialCmd",
    0x800D: "lSetLaserParaByUart",
    0x800F: "lSetLaserOnWithTime",
    0x8010: "lLaserDirectControl",
    0x8011: "lSetLaserOnTimeCount",
    0x8012: "lLaserOnWithFixTime",
    0x8013: "lSetLaserPWMCountClock",
    0x8014: "lSetLaserOnDelayCorPara",
    0x8015: "lSetLaserPWMInverse",
    0x8016: "lSetLaserOnLagTime",
    0x8017: "lSetLaserPowerVariable",
    0x8021: "lSetJumpSpeed",
    0x8022: "lSetMarkSpeed",
    0x8023: "lSetScanDelay",
    0x8024: "lSetJumpDelayWorkMode",
    0x8026: "lSelectScannerOutputMode",
    0x8027: "lAdjustScanner2DPos",
    0x8028: "lSetVariableFloat",
    0x8029: "lSetVariableInt",
    0x802A: "lSetVariableFloatToParam",
    0x802B: "lSetVariableIntToParam",
    0x802C: "lSetWobbleCurveParamter",
    0x8041: "lJumpAbs2D",
    0x8042: "lJumpRel2D",
    0x8043: "lJumpAbs2DWithPosDetect",
    0x8044: "lHardJumpAbs2D",
    0x8046: "lTimedJumpAbs2D",
    0x8061: "lMarkAbs2D",
    0x8062: "lMarkRel2DWithIOCheck",
    0x8063: "lMarkAbs2DWithPOD",
    0x8064: "lWritePODCtrlData",
    0x8065: "lMarkAbs2DWithPosDetect",
    0x8066: "lSendPosCoorData",
    0x8067: "lSetArcCenter",
    0x8068: "lMarkArcAbs2D",
    0x8069: "lTimedMarkAbs2D",
    0x806B: "lMarkAbs2DWithDashDot",
    0x806C: "lStartPODMark",
    0x806D: "lWriteDottedLineApCtrlData",
    0x806E: "lMarkAbs2DWithDottedLine",
    0x806F: "lSetDottedLinePosDealy",
    0x8081: "lSetEndOfList",
    0x8082: "lListDelay",
    0x8083: "lListNop",
    0x8084: "lListAutoChange",
    0x8085: "lListPause",
    0x8086: "lListJumpToSpecifiedIndex",
    0x8087: "lListJumpToIndexWithCompareCond",
    0x8088: "lListRepeat",
    0x8089: "lListUntil",
    0x808A: "lListIfIOCond",
    0x80B2: "lResetMatrix",
    0x80B3: "lAutoSelectListMatirx",
    0x80C1: "lSelect2DCorFile",
    0x80C2: "lSelectZCorrection",
    0x80C3: "lSelectDynZCorrection",
    0x80C4: "lSelectHRC2DCorFile",
    0x80D1: "lSetFreq10usSyn",
    0x80D2: "lSetScannerProtocal",
    0x80D3: "lSetMinJumpLength",
    0x80D4: "lResetCounter",
    0x80D5: "lSetCounter",
    0x80D6: "lStartMarkTimer",
    0x80D7: "lStopMarkTimer",
    0x80D8: "lSetCurveMarkPara",
    0x80D9: "lSetOutputPort",
    0x80DA: "lWaitForInputPort",
    0x80DB: "lSetInputPort0Mode",
    0x80DB: "lSetInputPortMode",
    0x80DC: "lClearInputPort0State",
    0x80DC: "lClearInputPortState",
    0x80DE: "lStartSaveScannerPosition",
    0x80DF: "lSetInputPortIn8_9Mode",
    0x80E0: "lClearInputPortIn8_9State",
    0x80E1: "lSetPositionDetectPara",
    0x80E2: "lSetListIndexObject",
    0x80E3: "lExecuteListWithIOCheck",
    0x80E4: "lStartSerialComWithCCDCmd",
    0x80E6: "lSetOutputPWMPara",
    0x80E7: "lStartFlyWaitWithSerialCom",
    0x80E8: "lStartLaserMonitorProcess",
    0x80E9: "lSetOutputBitPort",
    0x80EA: "lSetSkyWritingPara",
    0x80EB: "lSelectListMatrix",
    0x80EC: "lSetScannerTrackError",
    0x80ED: "lSetMarkStepPitchMode",
    0x80EE: "lResetFlyWaitLatchedPosBuf",
    0x80EF: "lSetFlyWaitPositionIndex",
    0x80F0: "lSetMinIntervalTriggerCond",
    0x80F1: "lSetOutputPortWithMask",
    0x80F2: "lSetInputPortFilterPara",
    0x80F3: "lSetMarkTimeIndex",
    0x80F4: "lChooseScannerRetStatusCode",
    0x80F5: "lSetExtCurveMarkPara",
    0x8100: "lMarkPixelLinePara1",
    0x8101: "lMarkPixelLinePara2",
    0x8102: "lMarkPixelLinePara3",
    0x8103: "lMarkPixelLine4",
    0x8110: "lSetFlyEnable",
    0x8111: "lResetFlyDistance",
    0x8112: "lFlyWaitDistance",
    0x8114: "lResetFlyCorrectionValue",
    0x8115: "lFlyWaitXYPosition",
    0x8116: "lFlyWaitCameraPositioning",
    0x8117: "lSetEncoderPara",
    0x8118: "lSetFlyX",
    0x8119: "lSetFlyY",
    0x811A: "lSetFlyRot",
    0x811B: "lSetSimulatorEncoder",
    0x811C: "lSetFlyFactorRatio",
    0x811D: "lEnableFlyCorrection",
    0x811E: "lLaserCtrlWithEncoderPosition",
    0x811F: "lFlyWaitRelDistance",
    0x8120: "lMarkAbs3D",
    0x8121: "lJumpAbs3D",
    0x8122: "lMarkAbs3DWithPosDetect",
    0x8123: "lJumpAbs3DWithPosDetect",
    0x8151: "lResetScanner",
    0x8152: "lReadListFile",
    0x8153: "lSetListLoop",
    0x8154: "lDoListLoop",
    0x8155: "lCheckIOStatus",
    0x8181: "lStepperInit",
    0x8187: "lStepperInit2",
    0x8188: "lStepperInit3",
    0x8182: "lStepperSingleAxisMove",
    0x8183: "lStepperMultiAxisMove",
    0x8184: "lStepperSingleAxisOrigin",
    0x8185: "lStepperMultiAxisOrigin",
    0x8186: "lStepperAxisReset",
    0x81B1: "lWritePCOApCtrlData",
    0x81D1: "lSetPSOPositionSource",
    0x81D2: "lSetPSOPulseWidth",
    0x81D3: "lSetPSOFunctionControl",
    0x81D3: "lResetPSO",
    0x81D3: "lStartPSO",
    0x81D3: "lStopPSO",
    0x81D4: "lSetPSODistanceCounter",
    0x81D5: "lSetPSOMaxInterval",
    0x8200: "lEnableRedDiode",
}

single_command_lookup = {
    "Unknown": "cLoad2DCorFile",
    "Unknown": "cSetJumpLookUpTable",
    "Unknown": "cSetLaserDelay",
    0x0001: "cConfigList",
    0x0002: "cLoadList",
    0x0003: "cExecuteList",
    0x0004: "cStopExecution",
    0x0005: "cPauseList",
    0x0006: "cRestartList",
    0x0007: "cListAutoChange",
    0x0008: "cCloseList",
    0x0009: "cResetList",
    0x000a: "cSetListMode",
    0x000c: "cForceSendList",
    0x000d: "cSetListPauseStatus",
    0x0021: "cSetLaserMode",
    0x0022: "cSetLaserActive",
    0x0023: "cLaserOn",
    0x0024: "cLaserOff",
    0x0026: "cSetLaserPower",
    0x0027: "cSetLaserTimeBase",
    0x0028: "cSetLaserFreq",
    0x0028: "cSetLaserPWMPara",
    0x0029: "cSetLaserStandByPara",
    0x002a: "cSetLaserQSwitchDelay",
    0x002b: "cSetRedDiodeGuide",
    0x002c: "cSetLaserSerialCmd",
    0x002d: "cSetLaserParaByUart",
    0x0032: "cLaserDirectControl",
    0x0033: "cSetLaserOnTimeCount",
    0x0034: "cLaserOnWithFixTime",
    0x0035: "cSetLaserPWMCountClock",
    0x0036: "cSetLaserOnDelayCorPara",
    0x0037: "cSetLaserOnLagTime",
    0x0038: "cSetLaserPWMInverse",
    0x0039: "cSetAutoLaserCtrlWithSpeed",
    0x003a: "cSetLaserPWMFPKPara",
    0x003b: "cSetLaseAnalogFPKPara",
    0x0044: "cSelect2DCorFile",
    0x0045: "cLoadZCorFile",
    0x0048: "cSelectZCorrection",
    0x0049: "cLoadZCorFile2",
    0x0081: "cSetXYParam",
    0x0082: "cSystemReset",
    0x0083: "cSetCalibrationFactor",
    0x0084: "cSetScannerProtocal",
    0x0085: "cSetMinJumpLength",
    0x0086: "cResetCounter",
    0x0087: "cSetCounter",
    0x0089: "cSetOutputPort",
    0x008a: "cWriteBoardMemory",
    0x008b: "cSetInputPort0Mode",
    0x008b: "cSetInputPortMode",
    0x008c: "cClearInputPort0State",
    0x008d: "cWriteBoardIdentifier",
    0x008e: "cResetScannerPosition",
    0x008f: "cEnableDynamicFocus",
    0x0090: "cSetInputPortIn8_9Mode",
    0x0090: "cSetInputPortMode2",
    0x0091: "cClearInputPortIn8_9State",
    0x0091: "cClearInputPortState",
    0x0092: "cSetPositionDetectPara",
    0x0093: "cSetInputPortWorkMode",
    0x0094: "cSetOutputPWMPara",
    0x00a1: "cSetEncoderPara",
    0x00a2: "cSetFlyX",
    0x00a3: "cSetFlyY",
    0x00a4: "cSetFlyTrackingError",
    0x00a5: "cSetFlyRot",
    0x00a7: "cResetEncoderCount",
    0x00a9: "cSetSimulatorEncoder",
    0x00aa: "cResetFlyDistance",
    0x00ac: "cResetFlyCorrectionValue",
    0x00ad: "cStartFlyVelocityMonitorProcess",
    0x00d1: "cStartSaveListFile",
    0x00d2: "cStopSaveListFile",
    0x00d3: "cStartSaveListMain",
    0x00d4: "cStopSaveListMain",
    0x00d5: "cSaveCorFile",
    0x00d6: "cEnableListSave",
    0x00f1: "cSetMatrix",
    0x00f2: "cSetListMatrix",
    0x0101: "cSetJumpSpeed",
    0x0102: "cSetMarkSpeed",
    0x0103: "cSetScanDelay",
    0x0104: "cSetJumpDelayWorkMode",
    0x0106: "cSelectScannerOutputMode",
    0x0107: "cSetScannerXYLagTime",
    0x0108: "cSetScannerRandomJitter",
    0x0109: "cSetWobbleCurveParamter",
    0x0145: "cLoadDynZCorFile",
    0x0147: "cLoadHRC2DCorFile",
    0x0150: "cSelectHRC2DCorFile",
    0x0151: "cLoadXYEncoderCorFile",
    0x0154: "cLoadMultiLayer2DCorFile",
    0x0157: "cEnableMultiLayer2DCorFile",
    0x0158: "cLoadMultiLayerZCorFile",
    0x015b: "cLoadMultiLayerCorAssistFile",
    0x0172: "cSetPolygonLaserDelay",
    0x0174: "cSetPolygonLaserOnTime",
    0x0175: "cStartPolygonMark",
    0x0176: "cStopPolygonMark",
    0x0177: "cSetLaserAdjustPara",
    0x0178: "cSetLaserEnergyFollowPara",
    0x0179: "cSetExtOutputPort",
    0x017a: "cWriteEncryptIDInfo",
    0x017b: "cSetOutputBitPort",
    0x017c: "cStartUSBMonitorProcess",
    0x017d: "cSendHeartBeatCmd",
    0x017e: "cSetSkyWritingPara",
    0x017f: "cGet3DPrintAnalogOutput",
    0x017f: "cSet3DPrintAnalogOutput",
    0x017f: "cSet3DPrintPWMOutput",
    0x017f: "cSet3DPrintSerialCmd",
    0x017f: "cStepperOutputCtrlSignal",
    0x0181: "cSetPolygonArcRadius",
    0x0182: "cStartLaserStatusMonitor",
    0x0183: "cSetScannerTrackError",
    0x0184: "cSetMarkStepPitchMode",
    0x0185: "cStartMainLoopIOCheckProcess",
    0x0186: "cSetStopMarkIOWorkPara",
    0x0187: "cSetPulseOutput",
    0x0188: "cSetMinIntervalTriggerCond",
    0x0189: "cSetDynFieldDistribution",
    0x018a: "cSetLaserIOSynOutput",
    0x018b: "cSetOutputPortWithMask",
    0x018c: "cStartScannerStatusMonitor",
    0x018d: "cSetInputPortFilterPara",
    0x018e: "cSetVariableFloat",
    0x018f: "cSetVariableInt",
    0x0190: "cSetBoardSerialNo",
    0x0191: "cSetOutputPortAutoSave",
    0x0192: "cStartInputportTriggerMonitor",
    0x0193: "cChooseScannerRetStatusCode",
    0x01b1: "cStepperInit",
    0x01b2: "cStepperSingleAxisMove",
    0x01b3: "cStepperMultiAxisMove",
    0x01b4: "cStepperSingleAxisOrigin",
    0x01b5: "cStepperMultiAxisOrigin",
    0x01b6: "cStepperAxisReset",
    0x01b7: "cStepperEnableAxisLimitSwitch",
    0x01b8: "cStepperEnableHandWheel",
    0x01b9: "cStepperAxisVelocityMode",
    0x01ba: "cStepperInit2",
    0x01bb: "cStepperInit3",
    0x01bc: "cStepperPositionClear",
    0x01bd: "cStepperPulseWidth",
    0x01e1: "cSetPCOEnable",
    0x01e2: "cSetPCOZIndexMode",
    0x01e3: "cSetPCOWorkPara",
    0x01e3: "cSetPCOWorkPara1",
    0x01e4: "cSetPCOWorkPara2",
    0x01e5: "cSetPCOPulseInterval",
    0x01e5: "cSetPCOPulseIntervalBase",
    0x01e6: "cSetPCOAPWid",
    0x01e7: "cSetPCOAPMode",
    0x01e8: "cSetPCOSingleAxisMove",
    0x01e9: "cSetPCOZIndexDelay",
    0x01ec: "cSetPCOWorkMode",
    0x01ed: "cSetPCOZCountEveryCycle",
    0x01f0: "cSetPCOExtTriggerEnable",
    0x01f1: "cSetPCOExtPulseMode",
    0x01f3: "cSetPCOExtPulseFreq",
    0x01f4: "cSetPCOSubDivisionPulseCount",
    0x01f5: "cSetPCOAxisFollowPara",
    0x01f6: "cSetPCOXAxisMove",
    0x01f9: "cSetPCOJitterTime",
    0x0231: "cSetPSOPositionSource",
    0x0232: "cSetPSOPulseWidth",
    0x0233: "cResetPSO",
    0x0233: "cSetPSOFunctionControl",
    0x0233: "cStartPSO",
    0x0233: "cStopPSO",
    0x0234: "cSetPSODistanceCounter",
    0x0235: "cSetPSOMaxInterval",
    0x0236: "cSetPSOFreqPara",
    0x0261: "cSetPolyScannerSpeed",
    0x0262: "cStartPolyScannerRun",
    0x0263: "cStopPolyScannerRun",
    0x0264: "cClearPolyScannerError",
    0x0266: "cSetPolyScannerSOSDelay",
    0x0268: "cSetPolyScannerFixedSOSWork",
    0x0269: "cSetPolyScannerSOSCorValue",
    0x026a: "cSetPolyScannerYCorPara",
    0x026c: "cSetPolyScannerPWMPara",
    0x0291: "cSendDspFirmware",
    0x0292: "cSendFPGAFirmware",
    0x0294: "cStartFirmwareUpdate",
}


BUSY = 0x04
READY = 0x20


def _bytes_to_words(r):
    b0 = r[1] << 8 | r[0]
    b1 = r[3] << 8 | r[2]
    b2 = r[5] << 8 | r[4]
    b3 = r[7] << 8 | r[6]
    return b0, b1, b2, b3


class GalvoController:
    """
    Galvo controller is tasked with sending queued data to the controller board and ensuring that the connection to the
    controller board is established to perform these actions.

    This should serve as a next generation command sequencer written from scratch for galvo lasers. The goal is to
    provide all the given commands in a coherent queue structure which provides correct sequences between list and
    single commands.
    """

    def __init__(
        self,
        service,
        x=0x8000,
        y=0x8000,
        mark_speed=None,
        goto_speed=None,
        light_speed=None,
        dark_speed=None,
        force_mock=False,
    ):
        self.service = service
        self.force_mock = force_mock
        self.is_shutdown = False  # Shutdown finished.

        name = self.service.label
        self.usb_log = service.channel(f"{name}/usb", buffer_size=500)
        self.usb_log.watch(lambda e: service.signal("pipe;usb_status", e))

        self.connection = None
        self._is_opening = False
        self._abort_open = False
        self._disable_connect = False

        self._light_bit = service.setting(int, "light_pin", 8)
        self._foot_bit = service.setting(int, "footpedal_pin", 15)

        self._last_x = x
        self._last_y = y
        self._mark_speed = mark_speed
        self._goto_speed = goto_speed
        self._light_speed = light_speed
        self._dark_speed = dark_speed

        self._ready = None
        self._speed = None
        self._travel_speed = None
        self._frequency = None
        self._power = None
        self._pulse_width = None

        self._delay_jump = None
        self._delay_on = None
        self._delay_off = None
        self._delay_poly = None
        self._delay_end = None

        self._wobble = None
        self._port_bits = 0
        self._machine_index = 0

        self.mode = DRIVER_STATE_RAPID
        self._active_list = None
        self._active_index = 0
        self._list_executing = False
        self._number_of_list_packets = 0
        self.paused = False

    @property
    def state(self):
        if self.mode == DRIVER_STATE_RAPID:
            return "idle", "idle"
        if self.paused:
            return "hold", "paused"
        if self.mode == DRIVER_STATE_RAW:
            return "busy", "raw"
        if self.mode == DRIVER_STATE_LIGHT:
            return "busy", "light"
        if self.mode == DRIVER_STATE_PROGRAM:
            return "busy", "program"

    def set_disable_connect(self, status):
        self._disable_connect = status

    def added(self):
        pass

    def service_detach(self):
        pass

    def shutdown(self, *args, **kwargs):
        self.is_shutdown = True

    @property
    def connected(self):
        if self.connection is None:
            return False
        return self.connection.is_open(self._machine_index)

    @property
    def is_connecting(self):
        if self.connection is None:
            return False
        return self._is_opening

    def abort_connect(self):
        self._abort_open = True
        self.usb_log("Connect Attempts Aborted")

    def disconnect(self):
        try:
            self.connection.close(self._machine_index)
        except (ConnectionError, ConnectionRefusedError, AttributeError):
            pass
        self.connection = None
        # Reset error to allow another attempt
        self.set_disable_connect(False)

    def connect_if_needed(self):
        if self._disable_connect:
            # After many failures automatic connects are disabled. We require a manual connection.
            self.abort_connect()
            self.connection = None
            raise ConnectionRefusedError(
                "DLC was unreachable. Explicit connect required."
            )
        if self.connection is None:
            if self.service.setting(bool, "mock", False) or self.force_mock:
                self.connection = MockConnection(self.usb_log)
                name = self.service.label
                self.connection.send = self.service.channel(f"{name}/send")
                self.connection.recv = self.service.channel(f"{name}/recv")
            else:
                self.connection = USBConnection(self.usb_log)
        self._is_opening = True
        self._abort_open = False
        count = 0
        while not self.connection.is_open(self._machine_index):
            try:
                if self.connection.open(self._machine_index) < 0:
                    raise ConnectionError
                self.init_laser()
            except (ConnectionError, ConnectionRefusedError):
                time.sleep(0.3)
                count += 1
                # self.usb_log(f"Error-Routine pass #{count}")
                if self.is_shutdown or self._abort_open:
                    self._is_opening = False
                    self._abort_open = False
                    return
                if self.connection.is_open(self._machine_index):
                    self.connection.close(self._machine_index)
                if count >= 10:
                    # We have failed too many times.
                    self._is_opening = False
                    self.set_disable_connect(True)
                    self.usb_log("Could not connect to the LMC controller.")
                    self.usb_log("Automatic connections disabled.")
                    raise ConnectionRefusedError(
                        "Could not connect to the DLC controller."
                    )
                time.sleep(0.3)
                continue
        self._is_opening = False
        self._abort_open = False

    def send(self, data, read=True):
        if self.is_shutdown:
            return -1, -1, -1, -1
        self.connect_if_needed()
        try:
            self.connection.write(self._machine_index, data)
        except ConnectionError:
            return -1, -1, -1, -1
        if read:
            try:
                r = self.connection.read(self._machine_index)
                return struct.unpack("<4H", r)
            except ConnectionError:
                return -1, -1, -1, -1

    def status(self):
        # TODO: Method of getting status is unknown.
        return 0
        # b0, b1, b2, b3 = self.get_version()
        # return b3

    #######################
    # MODE SHIFTS
    #######################

    def raw_mode(self):
        self.mode = DRIVER_STATE_RAW

    def rapid_mode(self):
        if self.mode == DRIVER_STATE_RAPID:
            return
        self.list_set_end_of_list()  # Ensure at least one list_end_of_list
        self._list_end()
        if not self._list_executing and self._number_of_list_packets:
            # If we never ran the list, and we sent some lists.
            self.command_execute_list()
        self._list_executing = False
        self._number_of_list_packets = 0
        self.wait_idle()
        self.port_off(bit=0)
        self.command_set_output_bit_port()
        self.mode = DRIVER_STATE_RAPID

    def raster_mode(self):
        self.program_mode()

    def program_mode(self):
        if self.mode == DRIVER_STATE_PROGRAM:
            return
        if self.mode == DRIVER_STATE_LIGHT:
            self.mode = DRIVER_STATE_PROGRAM
            self.light_off()
            self.port_on(bit=0)
            self.list_set_output_bit_port(self._port_bits)
        else:
            self.mode = DRIVER_STATE_PROGRAM
            self.command_reset_list()
            self.port_on(bit=0)
            self.list_set_output_bit_port(self._port_bits)
            self._ready = None
            self._speed = None
            self._travel_speed = None
            self._frequency = None
            self._power = None
            self._pulse_width = None

            self._delay_jump = None
            self._delay_on = None
            self._delay_off = None
            self._delay_poly = None
            self._delay_end = None
            self.list_set_laser_active()
            if self.service.delay_openmo != 0:
                self.list_set_laser_time_base(int(self.service.delay_openmo * 100))
            self.list_set_output_bit_port(self._port_bits)
            self.list_set_jump_speed(self.service.default_rapid_speed)

    def light_mode(self):
        if self.mode == DRIVER_STATE_LIGHT:
            return
        if self.mode == DRIVER_STATE_PROGRAM:
            self.port_off(bit=0)
            self.port_on(self._light_bit)
            self.list_set_output_bit_port(self._port_bits)
        else:
            self._ready = None
            self._speed = None
            self._travel_speed = None
            self._frequency = None
            self._power = None
            self._pulse_width = None

            self._delay_jump = None
            self._delay_on = None
            self._delay_off = None
            self._delay_poly = None
            self._delay_end = None

            self.command_reset_list()
            self.port_off(bit=0)
            self.port_on(self._light_bit)
            self.list_set_output_bit_port(self._port_bits)
        self.mode = DRIVER_STATE_LIGHT

    #######################
    # LIST APPENDING OPERATIONS
    #######################

    def _list_end(self):
        if self._active_list and self._active_index:
            self.wait_ready()
            while self.paused:
                time.sleep(0.3)
            self.send(self._active_list, False)
            self._number_of_list_packets += 1
            self._active_list = None
            self._active_index = 0
            if self._number_of_list_packets > 2 and not self._list_executing:
                if self.mode != DRIVER_STATE_RAW:
                    self.command_execute_list()
                self._list_executing = True

    def _list_new(self):
        self._active_list = copy(empty)
        self._active_index = 0

    def _list_write(self, command, v1=0, v2=0, v3=0, v4=0, v5=0):
        if self._active_index >= 0xC00:
            self._list_end()
        if self._active_list is None:
            self._list_new()
        index = self._active_index
        self._active_list[index : index + 12] = struct.pack(
            "<6H", int(command), int(v1), int(v2), int(v3), int(v4), int(v5)
        )
        self._active_index += 12

    def _command(self, command, v1=0, v2=0, v3=0, v4=0, v5=0, read=True):
        cmd = struct.pack(
            "<6H", int(command), int(v1), int(v2), int(v3), int(v4), int(v5)
        )
        return self.send(cmd, read=read)

    def raw_write(self, command, v1=0, v2=0, v3=0, v4=0, v5=0):
        """
        Write this raw command to value. Sends the correct way based on command value.

        @return:
        """
        if command >= 0x8000:
            self._list_write(command, v1, v2, v3, v4, v5)
        else:
            self._command(command, v1, v2, v3, v4, v5)

    def raw_clear(self):
        self._list_new()

    #######################
    # SETS FOR PLOTLIKES
    #######################

    def set_settings(self, settings):
        """
        Sets the primary settings. Rapid, frequency, speed, and timings.

        @param settings: The current settings dictionary
        @return:
        """
        if self.service.pulse_width_enabled:
            # Global Pulse Width is enabled.
            if str(settings.get("pulse_width_enabled", False)).lower() == "true":
                # Local Pulse Width value is enabled.
                # OpFiberYLPMPulseWidth
                self.list_set_pso_pulse_width(
                    int(settings.get("pulse_width", self.service.default_pulse_width))
                )
            else:
                # Only global is enabled, use global pulse width value.
                self.list_set_pso_pulse_width(self.service.default_pulse_width)

        if str(settings.get("rapid_enabled", False)).lower() == "true":
            self.list_set_jump_speed(
                float(settings.get("rapid_speed", self.service.default_rapid_speed))
            )
        else:
            self.list_set_jump_speed(self.service.default_rapid_speed)

        self.power(
            float(settings.get("power", self.service.default_power)) / 10.0
        )  # Convert power, out of 1000
        self.frequency(float(settings.get("frequency", self.service.default_frequency)))
        self.list_set_mark_speed(float(settings.get("speed", self.service.default_speed)))

        if str(settings.get("timing_enabled", False)).lower() == "true":
            self.list_set_laser_on_lag_time(
                settings.get("delay_laser_on", self.service.delay_laser_on)
            )
            # self.list_laser_off_delay(
            #     settings.get("delay_laser_off", self.service.delay_laser_off)
            # )
            # self.command_set_polygon_laser_delay(
            #     settings.get("delay_laser_polygon", self.service.delay_polygon)
            # )
        else:
            # Use globals
            self.list_set_laser_on_lag_time(self.service.delay_laser_on)
            # self.list_laser_off_delay(self.service.delay_laser_off)
            # self.command_set_polygon_laser_delay(self.service.delay_polygon)

    def set_wobble(self, settings):
        """
        Set the wobble parameters and mark modifications routines.

        @param settings: The dict setting to extract parameters from.
        @return:
        """
        if settings is None:
            self._wobble = None
            return
        wobble_enabled = str(settings.get("wobble_enabled", False)).lower() == "true"
        if not wobble_enabled:
            self._wobble = None
            return
        wobble_radius = settings.get("wobble_radius", "1.5mm")
        wobble_r = self.service.physical_to_device_length(wobble_radius, 0)[0]
        wobble_interval = settings.get("wobble_interval", "0.3mm")
        wobble_speed = settings.get("wobble_speed", 50.0)
        wobble_type = settings.get("wobble_type", "circle")
        wobble_interval = self.service.physical_to_device_length(wobble_interval, 0)[0]
        algorithm = self.service.lookup(f"wobble/{wobble_type}")
        if self._wobble is None:
            self._wobble = Wobble(
                algorithm=algorithm,
                radius=wobble_r,
                speed=wobble_speed,
                interval=wobble_interval,
            )
        else:
            # set our parameterizations
            self._wobble.algorithm = algorithm
            self._wobble.radius = wobble_r
            self._wobble.speed = wobble_speed

    #######################
    # PLOTLIKE SHORTCUTS
    #######################

    def mark(self, x, y):
        if x == self._last_x and y == self._last_y:
            return
        if x > 0xFFFF or x < 0 or y > 0xFFFF or y < 0:
            # Moves to out of range are not performed.
            return
        if self._mark_speed is not None:
            self.list_set_mark_speed(self._mark_speed)
        if self._wobble:
            for wx, wy in self._wobble(self._last_x, self._last_y, x, y):
                self.list_mark_abs_2d(wx, wy)
        else:
            self.list_mark_abs_2d(x, y)

    def goto(self, x, y, long=None, short=None, distance_limit=None):
        if x == self._last_x and y == self._last_y:
            return
        if x > 0xFFFF or x < 0 or y > 0xFFFF or y < 0:
            # Moves to out of range are not performed.
            return
        if self._goto_speed is not None:
            self.list_set_jump_speed(self._goto_speed)
        self.list_jump_abs_2d(x, y, long=long, short=short, distance_limit=distance_limit)

    def light(self, x, y, long=None, short=None, distance_limit=None):
        if x == self._last_x and y == self._last_y:
            return
        if x > 0xFFFF or x < 0 or y > 0xFFFF or y < 0:
            # Moves to out of range are not performed.
            return
        if self.light_on():
            self.list_set_output_bit_port(self._port_bits)
        if self._light_speed is not None:
            self.list_set_jump_speed(self._light_speed)
        self.list_jump_abs_2d(x, y, long=long, short=short, distance_limit=distance_limit)

    def dark(self, x, y, long=None, short=None, distance_limit=None):
        if x == self._last_x and y == self._last_y:
            return
        if x > 0xFFFF or x < 0 or y > 0xFFFF or y < 0:
            # Moves to out of range are not performed.
            return
        if self.light_off():
            self.list_set_output_bit_port(self._port_bits)
        if self._dark_speed is not None:
            self.list_set_jump_speed(self._dark_speed)
        self.list_jump_abs_2d(x, y, long=long, short=short, distance_limit=distance_limit)

    def set_xy(self, x, y):
        distance = int(abs(complex(x, y) - complex(self._last_x, self._last_y)))
        if distance > 0xFFFF:
            distance = 0xFFFF
        self.command_set_xy(x, y, distance=distance)

    def get_last_xy(self):
        return self._last_x, self._last_y

    #######################
    # Command Shortcuts
    #######################

    def is_busy(self):
        status = self.status()
        return bool(status & BUSY)

    def is_ready(self):
        status = self.status()
        return bool(status & READY)

    def is_ready_and_not_busy(self):
        if self.mode == DRIVER_STATE_RAW:
            return True
        status = self.status()
        return bool(status & READY) and not bool(status & BUSY)

    def wait_finished(self):
        if self.mode == DRIVER_STATE_RAW:
            return
        while not self.is_ready_and_not_busy():
            time.sleep(0.01)
            if self.is_shutdown:
                return

    def wait_ready(self):
        if self.mode == DRIVER_STATE_RAW:
            return
        while not self.is_ready():
            time.sleep(0.01)
            if self.is_shutdown:
                return

    def wait_idle(self):
        if self.mode == DRIVER_STATE_RAW:
            return
        while self.is_busy():
            time.sleep(0.01)
            if self.is_shutdown:
                return

    def abort(self, dummy_packet=True):
        if self.mode == DRIVER_STATE_RAW:
            return
        self.command_stop_execution()
        self.command_reset_list()
        if dummy_packet:
            self._list_new()
            self.list_set_end_of_list() # Ensure packet is sent on end.
            self._list_end()
            if not self._list_executing:
                self.command_execute_list()
        self._list_executing = False
        self._number_of_list_packets = 0
        self.port_off(bit=0)
        self.command_set_output_bit_port(self._port_bits)
        self.mode = DRIVER_STATE_RAPID

    def pause(self):
        if self.mode == DRIVER_STATE_RAW:
            return
        self.paused = True
        self.command_pause_list()

    def resume(self):
        if self.mode == DRIVER_STATE_RAW:
            return
        self.command_restart_list()
        self.paused = False

    def init_laser(self):
        if self.mode == DRIVER_STATE_RAW:
            return
        cor_file = self.service.corfile if self.service.corfile_enabled else None
        first_pulse_killer = self.service.first_pulse_killer
        pwm_pulse_width = self.service.pwm_pulse_width
        pwm_half_period = self.service.pwm_half_period
        standby_param_1 = self.service.standby_param_1
        standby_param_2 = self.service.standby_param_2
        timing_mode = self.service.timing_mode
        delay_mode = self.service.delay_mode
        laser_mode = self.service.laser_mode
        control_mode = self.service.control_mode
        fpk2_p1 = self.service.fpk2_p1
        fpk2_p2 = self.service.fpk2_p2
        fpk2_p3 = self.service.fpk2_p3
        fpk2_p4 = self.service.fpk2_p3
        fly_res_p1 = self.service.fly_res_p1
        fly_res_p2 = self.service.fly_res_p2
        fly_res_p3 = self.service.fly_res_p3
        fly_res_p4 = self.service.fly_res_p4
        self.command_system_reset()
        self.usb_log("Reset")
        self.write_correction_file(cor_file)
        self.usb_log("Correction File Sent")

        # self.enable_laser()
        # self.usb_log("Laser Enabled")

        self.command_laser_direct_control()
        self.usb_log("Control Mode")

        #
        # self.set_laser_mode(laser_mode)
        # self.usb_log("Laser Mode")

        self.command_set_laser_standby(standby_param_1, standby_param_2)
        self.usb_log("Setting Standby")

        self.command_set_pso_pulse_width(pwm_pulse_width)
        self.usb_log("Set PWM pulse width")

        self.usb_log("Ready")

    def power(self, power):
        """
        Accepts power in percent, automatically converts to power_ratio

        @param power:
        @return:
        """
        if self._power == power:
            return
        self._power = power
        self.list_set_laser_power(self._convert_power(power))

    def frequency(self, frequency):
        if self._frequency == frequency:
            return
        self._frequency = frequency
        self.list_set_laser_qswitch_delay(self._convert_frequency(frequency))

    def light_on(self):
        if not self.is_port(self._light_bit):
            self.port_on(self._light_bit)
            return True
        return False

    def light_off(self):
        if self.is_port(self._light_bit):
            self.port_off(self._light_bit)
            return True
        return False

    def is_port(self, bit):
        return bool((1 << bit) & self._port_bits)

    def port_on(self, bit):
        self._port_bits = self._port_bits | (1 << bit)

    def port_off(self, bit):
        self._port_bits = ~((~self._port_bits) | (1 << bit))

    def port_set(self, mask, values):
        self._port_bits &= ~mask  # Unset mask.
        self._port_bits |= values & mask  # Set masked bits.

    #######################
    # UNIT CONVERSIONS
    #######################

    def _convert_speed(self, speed):
        """
        Speed in the galvo is given in galvos/ms this means mm/s needs to multiply by galvos_per_mm
        and divide by 1000 (s/ms)

        @param speed:
        @return:
        """
        # return int(speed / 2)
        galvos_per_mm = abs(self.service.physical_to_device_length("1mm", "1mm")[0])
        return int(speed * galvos_per_mm / 1000.0)

    def _convert_frequency(self, frequency_khz):
        """
        Converts frequency to period.

        20000000.0 / frequency in hz

        @param frequency_khz: Frequency to convert
        @return:
        """
        return int(round(20000.0 / frequency_khz)) & 0xFFFF

    def _convert_power(self, power):
        """
        Converts power percent to int value
        @return:
        """
        return int(round(power * 0xFFF / 100.0))

    #######################
    # HIGH LEVEL OPERATIONS
    #######################

    def write_correction_file(self, filename):
        pass
        # if filename is None:
        #     # self.write_blank_correct_file()
        #     return
        # try:
        #     table = self._read_correction_file(filename)
        #     self._write_correction_table(table)
        # except OSError:
        #     # self.write_blank_correct_file()
        #     return

    @staticmethod
    def get_scale_from_correction_file(filename):
        with open(filename, "rb") as f:
            label = f.read(0x16)
            if label.decode("utf-16") == "LMC1COR_1.0":
                unk = f.read(2)
                return struct.unpack("63d", f.read(0x1F8))[43]
            else:
                unk = f.read(6)
                return struct.unpack("d", f.read(8))[0]

    def _read_float_correction_file(self, f):
        """
        Read table for cor files marked: LMC1COR_1.0
        @param f:
        @return:
        """
        table = []
        for j in range(65):
            for k in range(65):
                dx = int(round(struct.unpack("d", f.read(8))[0]))
                dx = dx if dx >= 0 else -dx + 0x8000
                dy = int(round(struct.unpack("d", f.read(8))[0]))
                dy = dy if dy >= 0 else -dy + 0x8000
                table.append([dx & 0xFFFF, dy & 0xFFFF])
        return table

    def _read_int_correction_file(self, f):
        table = []
        for j in range(65):
            for k in range(65):
                dx = int.from_bytes(f.read(4), "little", signed=True)
                dx = dx if dx >= 0 else -dx + 0x8000
                dy = int.from_bytes(f.read(4), "little", signed=True)
                dy = dy if dy >= 0 else -dy + 0x8000
                table.append([dx & 0xFFFF, dy & 0xFFFF])
        return table

    def _read_correction_file(self, filename):
        """
        Reads a standard .cor file and builds a table from that.

        @param filename:
        @return:
        """
        with open(filename, "rb") as f:
            label = f.read(0x16)
            if label.decode("utf-16") == "LMC1COR_1.0":
                header = f.read(0x1FA)
                return self._read_float_correction_file(f)
            else:
                header = f.read(0xE)
                return self._read_int_correction_file(f)

    def _write_correction_table(self, table):
        assert len(table) == 65 * 65

    #######################
    # COMMAND LIST COMMAND
    #######################

    def list_set_laser_mode(self, *data):
        self._list_write(lSetLaserMode, *data)

    def list_set_laser_active(self, *data):
        self._list_write(lSetLaserActive, *data)

    def list_laser_on(self, *data):
        self._list_write(lLaserOn, *data)

    def list_laser_off(self, *data):
        self._list_write(lLaserOff, *data)

    def list_set_laser_power(self, *data):
        self._list_write(lSetLaserPower, *data)

    def list_set_laser_time_base(self, *data):
        self._list_write(lSetLaserTimeBase, *data)

    def list_set_laser_pwm(self, *data):
        self._list_write(lSetLaserPWMPara, *data)

    def list_set_laser_standby(self, *data):
        self._list_write(lSetLaserStandByPara, *data)

    def list_set_laser_qswitch_delay(self, *data):
        self._list_write(lSetLaserQSwitchDelay, *data)

    def list_set_red_diode_guide(self, *data):
        self._list_write(lSetRedDiodeGuide, *data)

    def list_laser_serial_cmd(self, *data):
        self._list_write(lSetLaserSerialCmd, *data)

    def list_set_laser_parameter_by_uart(self, *data):
        self._list_write(lSetLaserParaByUart, *data)

    def list_set_laser_on_with_time(self, *data):
        self._list_write(lSetLaserOnWithTime, *data)

    def list_laser_direct_control(self, *data):
        self._list_write(lLaserDirectControl, *data)

    def list_set_laser_on_time_count(self, *data):
        self._list_write(lSetLaserOnTimeCount, *data)

    def list_laser_on_with_fix_time(self, *data):
        self._list_write(lLaserOnWithFixTime, *data)

    def list_set_laser_pwm_count_clock(self, *data):
        self._list_write(lSetLaserPWMCountClock, *data)

    def list_set_laser_on_delay_cor(self, *data):
        self._list_write(lSetLaserOnDelayCorPara, *data)

    def list_set_laser_pwm_inverse(self, *data):
        self._list_write(lSetLaserPWMInverse, *data)

    def list_set_laser_on_lag_time(self, delay):
        """
        Set laser on delay in microseconds
        @param delay:
        @return:
        """
        if self._delay_on == delay:
            return
        self._delay_on = delay
        self._list_write(
            lSetLaserOnLagTime, abs(delay), 0x0000 if delay > 0 else 0x8000
        )

    def list_set_laser_power_variable(self, *data):
        self._list_write(lSetLaserPowerVariable, *data)

    def list_set_jump_speed(self, speed):
        if self._travel_speed == speed:
            return
        self._travel_speed = speed
        c_speed = self._convert_speed(speed)
        if c_speed > 0xFFFF:
            c_speed = 0xFFFF
        self._list_write(lSetJumpSpeed, c_speed)

    def list_set_mark_speed(self, speed):
        """
        Sets the marking speed for the laser.

        @param speed:
        @return:
        """
        if self._speed == speed:
            return
        self._speed = speed
        c_speed = self._convert_speed(speed)
        if c_speed > 0xFFFF:
            c_speed = 0xFFFF
        self._list_write(lSetMarkSpeed, c_speed)

    def list_set_scan_delay(self, *data):
        self._list_write(lSetScanDelay, *data)

    def list_set_jump_delay_work_mode(self, delay):
        """
        Set laser jump delay in microseconds
        @param delay:
        @return:
        """
        if self._delay_jump == delay:
            return
        self._delay_jump = delay
        self._list_write(
            lSetJumpDelayWorkMode, abs(delay), 0x0000 if delay > 0 else 0x8000
        )

    def list_select_scanner_output_mode(self, *data):
        self._list_write(lSelectScannerOutputMode, *data)

    def list_adjust_scanner_2d_pos(self, *data):
        self._list_write(lAdjustScanner2DPos, *data)

    def list_set_variable_float(self, *data):
        self._list_write(lSetVariableFloat, *data)

    def list_set_variable_int(self, *data):
        self._list_write(lSetVariableInt, *data)

    def list_set_variable_float_to_param(self, *data):
        self._list_write(lSetVariableFloatToParam, *data)

    def list_set_variable_int_to_param(self, *data):
        self._list_write(lSetVariableIntToParam, *data)

    def list_set_wobble_curve_parameter(self, *data):
        self._list_write(lSetWobbleCurveParamter, *data)

    def list_jump_abs_2d(self, x, y, short=None, long=None, distance_limit=None):
        distance = int(abs(complex(x, y) - complex(self._last_x, self._last_y)))
        if distance_limit and distance > distance_limit:
            delay = long
        else:
            delay = short
        if distance > 0xFFFF:
            distance = 0xFFFF
        angle = 0
        if delay:
            self.list_set_jump_delay_work_mode(delay)
        x = int(x)
        y = int(y)
        self._list_write(lJumpAbs2D, x, y, angle, distance)
        self._last_x = x
        self._last_y = y

    def list_jump_rel_2d(self, *data):
        self._list_write(lJumpRel2D, *data)

    def list_jump_abs_2d_with_position_detect(self, *data):
        self._list_write(lJumpAbs2DWithPosDetect, *data)

    def list_hard_jump_abs_2d(self, *data):
        self._list_write(lHardJumpAbs2D, *data)

    def list_timed_jump_abs_2d(self, *data):
        self._list_write(lTimedJumpAbs2D, *data)

    def list_mark_abs_2d(self, x, y, angle=0):
        distance = int(abs(complex(x, y) - complex(self._last_x, self._last_y)))
        if distance > 0xFFFF:
            distance = 0xFFFF
        x = int(x)
        y = int(y)
        self._list_write(lMarkAbs2D, x, y, angle, distance)
        self._last_x = x
        self._last_y = y

    def list_mark_rel_2d_with_io_check(self, *data):
        self._list_write(lMarkRel2DWithIOCheck, *data)

    def list_mark_abs_2d_with_pod(self, *data):
        self._list_write(lMarkAbs2DWithPOD, *data)

    def list_write_pod_control_data(self, *data):
        self._list_write(lWritePODCtrlData, *data)

    def list_mark_abs_2d_with_position_detect(self, *data):
        self._list_write(lMarkAbs2DWithPosDetect, *data)

    def list_send_pos_coor_data(self, *data):
        self._list_write(lSendPosCoorData, *data)

    def list_set_arc_center(self, *data):
        self._list_write(lSetArcCenter, *data)

    def list_mark_arc_abs_2d(self, *data):
        self._list_write(lMarkArcAbs2D, *data)

    def list_timed_mark_abs_2d(self, *data):
        self._list_write(lTimedMarkAbs2D, *data)

    def list_mark_abs_2d_with_dash_dot(self, *data):
        self._list_write(lMarkAbs2DWithDashDot, *data)

    def list_start_pod_mark(self, *data):
        self._list_write(lStartPODMark, *data)

    def list_write_dotted_line_ap_control_data(self, *data):
        self._list_write(lWriteDottedLineApCtrlData, *data)

    def list_mark_abs_2d_with_dotted_line(self, *data):
        self._list_write(lMarkAbs2DWithDottedLine, *data)

    def list_set_dotted_line_position_delay(self, *data):
        self._list_write(lSetDottedLinePosDealy, *data)

    def list_set_end_of_list(self):
        self._list_write(lSetEndOfList)

    def list_list_delay(self, *data):
        self._list_write(lListDelay, *data)

    def list_list_nop(self, *data):
        self._list_write(lListNop, *data)

    def list_list_auto_change(self, *data):
        self._list_write(lListAutoChange, *data)

    def list_list_pause(self, *data):
        self._list_write(lListPause, *data)

    def list_list_jump_to_specific_index(self, *data):
        self._list_write(lListJumpToSpecifiedIndex, *data)

    def list_list_jump_to_index_with_compare_condition(self, *data):
        self._list_write(lListJumpToIndexWithCompareCond, *data)

    def list_list_repeat(self, *data):
        self._list_write(lListRepeat, *data)

    def list_list_until(self, *data):
        self._list_write(lListUntil, *data)

    def list_list_if_io_cond(self, *data):
        self._list_write(lListIfIOCond, *data)

    def list_reset_matrix(self, *data):
        self._list_write(lResetMatrix, *data)

    def list_auto_select_list_matrix(self, *data):
        self._list_write(lAutoSelectListMatirx, *data)

    def list_select_2d_cor_file(self, *data):
        self._list_write(lSelect2DCorFile, *data)

    def list_select_z_correction(self, *data):
        self._list_write(lSelectZCorrection, *data)

    def list_select_dynamic_z_correction(self, *data):
        self._list_write(lSelectDynZCorrection, *data)

    def list_select_hrc_2d_correction(self, *data):
        self._list_write(lSelectHRC2DCorFile, *data)

    def list_set_frequency_syn(self, *data):
        self._list_write(lSetFreq10usSyn, *data)

    def list_set_scanner_protocol(self, *data):
        self._list_write(lSetScannerProtocal, *data)

    def list_set_min_jump_length(self, *data):
        self._list_write(lSetMinJumpLength, *data)

    def list_reset_counter(self, *data):
        self._list_write(lResetCounter, *data)

    def list_set_counter(self, *data):
        self._list_write(lSetCounter, *data)

    def list_start_mark_timer(self, *data):
        self._list_write(lStartMarkTimer, *data)

    def list_stop_mark_timer(self, *data):
        self._list_write(lStopMarkTimer, *data)

    def list_set_curve_mark_parameter(self, *data):
        self._list_write(lSetCurveMarkPara, *data)

    def list_set_output_port(self, *data):
        self._list_write(lSetOutputPort, *data)

    def list_wait_for_input_port(self, *data):
        self._list_write(lWaitForInputPort, *data)

    def list_set_input_port_0_mode(self, *data):
        self._list_write(lSetInputPort0Mode, *data)

    def list_set_input_port_mode(self, *data):
        self._list_write(lSetInputPortMode, *data)

    def list_clear_input_port_0_state(self, *data):
        self._list_write(lClearInputPort0State, *data)

    def list_clear_input_port_state(self, *data):
        self._list_write(lClearInputPortState, *data)

    def list_start_save_scanner_position(self, *data):
        self._list_write(lStartSaveScannerPosition, *data)

    def list_set_input_port_in_8_9_mode(self, *data):
        self._list_write(lSetInputPortIn8_9Mode, *data)

    def list_clear_input_port_in_8_9_state(self, *data):
        self._list_write(lClearInputPortIn8_9State, *data)

    def list_set_position_detection_param(self, *data):
        self._list_write(lSetPositionDetectPara, *data)

    def list_set_list_index_object(self, *data):
        self._list_write(lSetListIndexObject, *data)

    def list_execute_list_with_io_check(self, *data):
        self._list_write(lExecuteListWithIOCheck, *data)

    def list_start_serial_com_with_ccd_cmd(self, *data):
        self._list_write(lStartSerialComWithCCDCmd, *data)

    def list_set_output_pwm_parameter(self, *data):
        self._list_write(lSetOutputPWMPara, *data)

    def list_set_fly_wait_with_serial_com(self, *data):
        self._list_write(lStartFlyWaitWithSerialCom, *data)

    def list_set_laser_monitor_process(self, *data):
        self._list_write(lStartLaserMonitorProcess, *data)

    def list_set_output_bit_port(self, *data):
        self._list_write(lSetOutputBitPort, *data)

    def list_set_sky_writing_parameter(self, *data):
        self._list_write(lSetSkyWritingPara, *data)

    def list_select_list_matrix(self, *data):
        self._list_write(lSelectListMatrix, *data)

    def list_set_scanner_track_error(self, *data):
        self._list_write(lSetScannerTrackError, *data)

    def list_set_mark_step_pitch_mode(self, *data):
        self._list_write(lSetMarkStepPitchMode, *data)

    def list_reset_fly_wait_latched_position_buffer(self, *data):
        self._list_write(lResetFlyWaitLatchedPosBuf, *data)

    def list_set_fly_wait_position_index(self, *data):
        self._list_write(lSetFlyWaitPositionIndex, *data)

    def list_set_min_interval_trigger_condition(self, *data):
        self._list_write(lSetMinIntervalTriggerCond, *data)

    def list_set_output_port_with_mask(self, *data):
        self._list_write(lSetOutputPortWithMask, *data)

    def list_set_output_port_filter_parameter(self, *data):
        self._list_write(lSetInputPortFilterPara, *data)

    def list_set_mark_time_index(self, *data):
        self._list_write(lSetMarkTimeIndex, *data)

    def list_choose_scanner_return_status_code(self, *data):
        self._list_write(lChooseScannerRetStatusCode, *data)

    def list_set_extended_curve_mark_parameter(self, *data):
        self._list_write(lSetExtCurveMarkPara, *data)

    def list_mark_pixel_line_parameter1(self, *data):
        self._list_write(lMarkPixelLinePara1, *data)

    def list_mark_pixel_line_parameter2(self, *data):
        self._list_write(lMarkPixelLinePara2, *data)

    def list_mark_pixel_line_parameter3(self, *data):
        self._list_write(lMarkPixelLinePara3, *data)

    def list_mark_pixel_line_parameter4(self, *data):
        self._list_write(lMarkPixelLine4, *data)

    def list_set_fly_enable(self, *data):
        self._list_write(lSetFlyEnable, *data)

    def list_reset_fly_distance(self, *data):
        self._list_write(lResetFlyDistance, *data)

    def list_fly_wait_distance(self, *data):
        self._list_write(lFlyWaitDistance, *data)

    def list_reset_fly_correction_value(self, *data):
        self._list_write(lResetFlyCorrectionValue, *data)

    def list_fly_wait_xy_position(self, *data):
        self._list_write(lFlyWaitXYPosition, *data)

    def list_fly_wait_camera_positioning(self, *data):
        self._list_write(lFlyWaitCameraPositioning, *data)

    def list_set_encoder_parameter(self, *data):
        self._list_write(lSetEncoderPara, *data)

    def list_set_fly_x(self, *data):
        self._list_write(lSetFlyX, *data)

    def list_set_fly_y(self, *data):
        self._list_write(lSetFlyY, *data)

    def list_set_fly_rotation(self, *data):
        self._list_write(lSetFlyRot, *data)

    def list_set_simulator_encoder(self, *data):
        self._list_write(lSetSimulatorEncoder, *data)

    def list_set_fly_factor_ratio(self, *data):
        self._list_write(lSetFlyFactorRatio, *data)

    def list_enable_fly_correction(self, *data):
        self._list_write(lEnableFlyCorrection, *data)

    def list_laser_control_with_encoder_position(self, *data):
        self._list_write(lLaserCtrlWithEncoderPosition, *data)

    def list_fly_wait_relative_distance(self, *data):
        self._list_write(lFlyWaitRelDistance, *data)

    def list_mark_abs_3d(self, *data):
        self._list_write(lMarkAbs3D, *data)

    def list_jump_abs_3d(self, *data):
        self._list_write(lJumpAbs3D, *data)

    def list_mark_abs3d_with_position_detect(self, *data):
        self._list_write(lMarkAbs3DWithPosDetect, *data)

    def list_jump_abs_3d_with_pos_detect(self, *data):
        self._list_write(lJumpAbs3DWithPosDetect, *data)

    def list_reset_scanner(self, *data):
        self._list_write(lResetScanner, *data)

    def list_read_list_file(self, *data):
        self._list_write(lReadListFile, *data)

    def list_set_list_loop(self, *data):
        self._list_write(lSetListLoop, *data)

    def list_do_list_loop(self, *data):
        self._list_write(lDoListLoop, *data)

    def list_check_io_status(self, *data):
        self._list_write(lCheckIOStatus, *data)

    def list_stepper_init(self, *data):
        self._list_write(lStepperInit, *data)

    def list_stepper_init2(self, *data):
        self._list_write(lStepperInit2, *data)

    def list_stepper_init3(self, *data):
        self._list_write(lStepperInit3, *data)

    def list_stepper_single_axis_move(self, *data):
        self._list_write(lStepperSingleAxisMove, *data)

    def list_stepper_multi_axis_move(self, *data):
        self._list_write(lStepperMultiAxisMove, *data)

    def list_stepper_single_axis_origin(self, *data):
        self._list_write(lStepperSingleAxisOrigin, *data)

    def list_stepper_multi_axis_origin(self, *data):
        self._list_write(lStepperMultiAxisOrigin, *data)

    def list_stepper_axis_reset(self, *data):
        self._list_write(lStepperAxisReset, *data)

    def list_write_pco_ap_control_data(self, *data):
        self._list_write(lWritePCOApCtrlData, *data)

    def list_set_pso_position_source(self, *data):
        self._list_write(lSetPSOPositionSource, *data)

    def list_set_pso_pulse_width(self, *data):
        self._list_write(lSetPSOPulseWidth, *data)

    def list_set_pso_functional_control(self, *data):
        self._list_write(lSetPSOFunctionControl, *data)

    def list_reset_pso(self, *data):
        self._list_write(lResetPSO, *data)

    def list_start_pso(self, *data):
        self._list_write(lStartPSO, *data)

    def list_stop_pso(self, *data):
        self._list_write(lStopPSO, *data)

    def list_set_pso_distance_counter(self, *data):
        self._list_write(lSetPSODistanceCounter, *data)

    def list_set_pso_max_interval(self, *data):
        self._list_write(lSetPSOMaxInterval, *data)

    def list_set_enable_red_diode(self, *data):
        self._list_write(lEnableRedDiode, *data)

    #######################
    # COMMAND LIST SHORTCUTS
    #######################

    def command_config_list(self):
        return self._command(cConfigList)

    def command_load_list(self):
        return self._command(cLoadList)

    def command_execute_list(self):
        return self._command(cExecuteList)

    def command_stop_execution(self):
        return self._command(cStopExecution)

    def command_pause_list(self):
        return self._command(cPauseList)

    def command_restart_list(self):
        return self._command(cRestartList)

    def command_list_auto_change(self):
        return self._command(cListAutoChange)

    def command_close_list(self):
        return self._command(cCloseList)

    def command_reset_list(self):
        return self._command(cResetList)

    def command_set_list_mode(self):
        return self._command(cSetListMode)

    def command_force_send_list(self):
        return self._command(cForceSendList)

    def command_set_list_pause_status(self):
        return self._command(cSetListPauseStatus)

    def command_set_laser_mode(self):
        return self._command(cSetLaserMode)

    def command_set_laser_active(self):
        return self._command(cSetLaserActive)

    def command_laser_on(self):
        return self._command(cLaserOn)

    def command_laser_off(self):
        return self._command(cLaserOff)

    def command_set_laser_power(self):
        return self._command(cSetLaserPower)

    def command_set_laser_time_base(self):
        return self._command(cSetLaserTimeBase)

    def command_set_laser_frequency(self):
        return self._command(cSetLaserFreq)

    def command_set_laser_pwm(self):
        return self._command(cSetLaserPWMPara)

    def command_set_laser_standby(self, *data):
        return self._command(cSetLaserStandByPara, *data)

    def command_set_laser_qswitch_delay(self):
        return self._command(cSetLaserQSwitchDelay)

    def command_set_red_diode_guide(self):
        return self._command(cSetRedDiodeGuide)

    def command_set_laser_serial_command(self):
        return self._command(cSetLaserSerialCmd)

    def command_set_laser_parameter_by_uart(self):
        return self._command(cSetLaserParaByUart)

    def command_laser_direct_control(self):
        return self._command(cLaserDirectControl)

    def command_set_laser_on_time_count(self):
        return self._command(cSetLaserOnTimeCount)

    def command_laser_on_with_fix_time(self):
        return self._command(cLaserOnWithFixTime)

    def command_set_laser_pwm_count_clock(self):
        return self._command(cSetLaserPWMCountClock)

    def command_set_laser_on_delay_correction(self):
        return self._command(cSetLaserOnDelayCorPara)

    def command_set_laser_on_lag_time(self):
        return self._command(cSetLaserOnLagTime)

    def command_set_laser_pwm_inverse(self):
        return self._command(cSetLaserPWMInverse)

    def command_set_auto_laser_control_with_speed(self):
        return self._command(cSetAutoLaserCtrlWithSpeed)

    def command_set_laser_pwm_fpk(self):
        return self._command(cSetLaserPWMFPKPara)

    def command_set_laser_analog_pfk(self):
        return self._command(cSetLaseAnalogFPKPara)

    def command_select_2d_cor_file(self):
        return self._command(cSelect2DCorFile)

    def command_load_z_cor_file(self):
        return self._command(cLoadZCorFile)

    def command_select_z_cor_file(self):
        return self._command(cSelectZCorrection)

    def command_load_z_cor_file2(self):
        return self._command(cLoadZCorFile2)

    def command_set_xy(self, x, y, angle=0, distance=0):
        self._last_x = x
        self._last_y = y
        return self._command(cSetXYParam, int(x), int(y), int(angle), int(distance))

    def command_system_reset(self):
        return self._command(cSystemReset)

    def command_set_calibration_factor(self):
        return self._command(cSetCalibrationFactor)

    def command_set_scanner_protocol(self):
        return self._command(cSetScannerProtocal)

    def command_set_min_jump_length(self):
        return self._command(cSetMinJumpLength)

    def command_reset_counter(self):
        return self._command(cResetCounter)

    def command_set_counter(self):
        return self._command(cSetCounter)

    def command_set_output_port(self):
        return self._command(cSetOutputPort)

    def command_write_board_memory(self):
        return self._command(cWriteBoardMemory)

    def command_set_input_port_0_mode(self):
        return self._command(cSetInputPort0Mode)

    def command_set_input_port_mode(self):
        return self._command(cSetInputPortMode)

    def command_clear_input_port_0_state(self):
        return self._command(cClearInputPort0State)

    def command_write_board_identifier(self):
        return self._command(cWriteBoardIdentifier)

    def command_reset_scanner_position(self):
        return self._command(cResetScannerPosition)

    def command_enable_dynamic_focus(self):
        return self._command(cEnableDynamicFocus)

    def command_set_input_port_in_8_9_mode(self):
        return self._command(cSetInputPortIn8_9Mode)

    def command_set_input_port_mode_2(self):
        return self._command(cSetInputPortMode2)

    def command_clear_input_port_in_8_9_state(self):
        return self._command(cClearInputPortIn8_9State)

    def command_clear_input_port_state(self):
        return self._command(cClearInputPortState)

    def command_set_position_detection(self):
        return self._command(cSetPositionDetectPara)

    def command_set_input_port_work_mode(self):
        return self._command(cSetInputPortWorkMode)

    def command_set_output_pwm(self):
        return self._command(cSetOutputPWMPara)

    def command_set_encoder(self):
        return self._command(cSetEncoderPara)

    def command_set_fly_x(self):
        return self._command(cSetFlyX)

    def command_set_fly_y(self):
        return self._command(cSetFlyY)

    def command_set_fly_tracking_error(self):
        return self._command(cSetFlyTrackingError)

    def command_set_fly_rotation(self):
        return self._command(cSetFlyRot)

    def command_reset_encoder_count(self):
        return self._command(cResetEncoderCount)

    def command_set_simulator_encoder(self):
        return self._command(cSetSimulatorEncoder)

    def command_reset_fly_distance(self):
        return self._command(cResetFlyDistance)

    def command_reset_fly_correction_value(self):
        return self._command(cResetFlyCorrectionValue)

    def command_start_fly_velocity_monitor_process(self):
        return self._command(cStartFlyVelocityMonitorProcess)

    def command_start_save_list_file(self):
        return self._command(cStartSaveListFile)

    def command_stop_save_list_file(self):
        return self._command(cStopSaveListFile)

    def command_start_save_list_main(self):
        return self._command(cStartSaveListMain)

    def command_stop_save_list_main(self):
        return self._command(cStopSaveListMain)

    def command_save_cor_file(self):
        return self._command(cSaveCorFile)

    def command_enable_list_save(self):
        return self._command(cEnableListSave)

    def command_set_matrix(self):
        return self._command(cSetMatrix)

    def command_set_list_matrix(self):
        return self._command(cSetListMatrix)

    def command_set_jump_speed(self):
        return self._command(cSetJumpSpeed)

    def command_set_mark_speed(self):
        return self._command(cSetMarkSpeed)

    def command_set_scan_delay(self):
        return self._command(cSetScanDelay)

    def command_set_jump_delay_work_mode(self):
        return self._command(cSetJumpDelayWorkMode)

    def command_select_scanner_output_mode(self):
        return self._command(cSelectScannerOutputMode)

    def command_set_scanner_xy_lag_time(self):
        return self._command(cSetScannerXYLagTime)

    def command_set_scanner_random_jitter(self):
        return self._command(cSetScannerRandomJitter)

    def command_set_wobble_curve(self):
        return self._command(cSetWobbleCurveParamter)

    def command_load_dynamic_z_cor_file(self):
        return self._command(cLoadDynZCorFile)

    def command_load_hrc_2d_cor_file(self):
        return self._command(cLoadHRC2DCorFile)

    def command_select_hrc_2d_cor_file(self):
        return self._command(cSelectHRC2DCorFile)

    def command_load_xy_encoder_cor_file(self):
        return self._command(cLoadXYEncoderCorFile)

    def command_load_multi_layer_2d_cor_file(self):
        return self._command(cLoadMultiLayer2DCorFile)

    def command_enable_multi_layer_2d_cor_file(self):
        return self._command(cEnableMultiLayer2DCorFile)

    def command_load_multilayer_z_cor_file(self):
        return self._command(cLoadMultiLayerZCorFile)

    def command_load_multi_layer_cor_assist_file(self):
        return self._command(cLoadMultiLayerCorAssistFile)

    def command_set_polygon_laser_delay(self):
        return self._command(cSetPolygonLaserDelay)

    def command_set_polygon_laser_on_time(self):
        return self._command(cSetPolygonLaserOnTime)

    def command_start_polygon_mark(self):
        return self._command(cStartPolygonMark)

    def command_stop_polygon_mark(self):
        return self._command(cStopPolygonMark)

    def command_set_laser_adjust(self):
        return self._command(cSetLaserAdjustPara)

    def command_set_laser_energy_follow(self):
        return self._command(cSetLaserEnergyFollowPara)

    def command_set_ext_output_port(self):
        return self._command(cSetExtOutputPort)

    def command_write_encrypt_id_info(self):
        return self._command(cWriteEncryptIDInfo)

    def command_set_output_bit_port(self, *data):
        return self._command(cSetOutputBitPort, *data)

    def command_start_usb_monitor_process(self):
        return self._command(cStartUSBMonitorProcess)

    def command_send_heart_beat_command(self):
        return self._command(cSendHeartBeatCmd)

    def command_set_sky_writing(self):
        return self._command(cSetSkyWritingPara)

    def command_get_3d_print_analog_output(self):
        return self._command(cGet3DPrintAnalogOutput)

    def command_set_3d_print_analog_output(self):
        return self._command(cSet3DPrintAnalogOutput)

    def command_set_3d_print_pwm_output(self):
        return self._command(cSet3DPrintPWMOutput)

    def command_set_3d_print_serial_command(self):
        return self._command(cSet3DPrintSerialCmd)

    def command_stepper_output_control_signal(self):
        return self._command(cStepperOutputCtrlSignal)

    def command_set_polygon_arc_radius(self):
        return self._command(cSetPolygonArcRadius)

    def command_start_laser_status_monitor(self):
        return self._command(cStartLaserStatusMonitor)

    def command_set_scanner_track_error(self):
        return self._command(cSetScannerTrackError)

    def command_set_mark_step_pitch_mode(self):
        return self._command(cSetMarkStepPitchMode)

    def command_start_main_loop_io_check_process(self):
        return self._command(cStartMainLoopIOCheckProcess)

    def command_set_stop_mark_io_work(self):
        return self._command(cSetStopMarkIOWorkPara)

    def command_set_pulse_output(self):
        return self._command(cSetPulseOutput)

    def command_set_minimum_interval_trigger_condition(self):
        return self._command(cSetMinIntervalTriggerCond)

    def command_set_dynamic_field_distribution(self):
        return self._command(cSetDynFieldDistribution)

    def command_set_laser_io_syn_output(self):
        return self._command(cSetLaserIOSynOutput)

    def command_set_output_port_with_mask(self):
        return self._command(cSetOutputPortWithMask)

    def command_start_scanner_status_monitor(self):
        return self._command(cStartScannerStatusMonitor)

    def command_set_input_port_filter(self):
        return self._command(cSetInputPortFilterPara)

    def command_set_variable_float(self):
        return self._command(cSetVariableFloat)

    def command_set_variable_int(self):
        return self._command(cSetVariableInt)

    def command_set_board_serial_number(self):
        return self._command(cSetBoardSerialNo)

    def command_set_output_port_auto_save(self):
        return self._command(cSetOutputPortAutoSave)

    def command_start_inputport_trigger_monitor(self):
        return self._command(cStartInputportTriggerMonitor)

    def command_choose_scanner_return_status_code(self):
        return self._command(cChooseScannerRetStatusCode)

    def command_stepper_init(self):
        return self._command(cStepperInit)

    def command_stepper_single_axis_move(self):
        return self._command(cStepperSingleAxisMove)

    def command_stepper_multi_axis_move(self):
        return self._command(cStepperMultiAxisMove)

    def command_stepper_single_axis_origin(self):
        return self._command(cStepperSingleAxisOrigin)

    def command_stepper_multi_axis_origin(self):
        return self._command(cStepperMultiAxisOrigin)

    def command_stepper_axis_reset(self):
        return self._command(cStepperAxisReset)

    def command_stepper_enable_axis_limit_switch(self):
        return self._command(cStepperEnableAxisLimitSwitch)

    def command_stepper_enable_hand_wheel(self):
        return self._command(cStepperEnableHandWheel)

    def command_stepper_axis_velocity_mode(self):
        return self._command(cStepperAxisVelocityMode)

    def command_stepper_init2(self):
        return self._command(cStepperInit2)

    def command_stepper_init3(self):
        return self._command(cStepperInit3)

    def command_stepper_position_clear(self):
        return self._command(cStepperPositionClear)

    def command_stepper_pulse_width(self):
        return self._command(cStepperPulseWidth)

    def command_set_pco_enable(self):
        return self._command(cSetPCOEnable)

    def command_set_pco_z_index_mode(self):
        return self._command(cSetPCOZIndexMode)

    def command_set_pco_work(self):
        return self._command(cSetPCOWorkPara)

    def command_set_pco_work1(self):
        return self._command(cSetPCOWorkPara1)

    def command_set_pco_work2(self):
        return self._command(cSetPCOWorkPara2)

    def command_set_pco_pulse_interval(self):
        return self._command(cSetPCOPulseInterval)

    def command_set_pco_pulse_interval_base(self):
        return self._command(cSetPCOPulseIntervalBase)

    def command_set_pco_ap_width(self):
        return self._command(cSetPCOAPWid)

    def command_set_pco_ap_mode(self):
        return self._command(cSetPCOAPMode)

    def command_set_pco_single_axis_move(self):
        return self._command(cSetPCOSingleAxisMove)

    def command_set_pco_z_index_delay(self):
        return self._command(cSetPCOZIndexDelay)

    def command_set_pco_work_mode(self):
        return self._command(cSetPCOWorkMode)

    def command_set_pco_z_count_every_cycle(self):
        return self._command(cSetPCOZCountEveryCycle)

    def command_set_pco_ext_trigger_enable(self):
        return self._command(cSetPCOExtTriggerEnable)

    def command_set_pco_ext_pulse_mode(self):
        return self._command(cSetPCOExtPulseMode)

    def command_set_pco_ext_pulse_frequency(self):
        return self._command(cSetPCOExtPulseFreq)

    def command_set_pco_sub_division_pulse_count(self):
        return self._command(cSetPCOSubDivisionPulseCount)

    def command_set_pco_axis_follow(self):
        return self._command(cSetPCOAxisFollowPara)

    def command_set_pco_x_axis_move(self):
        return self._command(cSetPCOXAxisMove)

    def command_set_pco_jitter_time(self):
        return self._command(cSetPCOJitterTime)

    def command_set_pso_position_source(self):
        return self._command(cSetPSOPositionSource)

    def command_set_pso_pulse_width(self, *data):
        return self._command(cSetPSOPulseWidth, *data)

    def command_reset_pso(self):
        return self._command(cResetPSO)

    def command_set_pso_function_control(self):
        return self._command(cSetPSOFunctionControl)

    def command_start_pso(self):
        return self._command(cStartPSO)

    def command_stop_pso(self):
        return self._command(cStopPSO)

    def command_set_pso_distance_counter(self):
        return self._command(cSetPSODistanceCounter)

    def command_set_pso_max_interval(self):
        return self._command(cSetPSOMaxInterval)

    def command_set_pso_frequency(self):
        return self._command(cSetPSOFreqPara)

    def command_set_poly_scanner_speed(self):
        return self._command(cSetPolyScannerSpeed)

    def command_start_poly_scanner_run(self):
        return self._command(cStartPolyScannerRun)

    def command_stop_poly_scanner_run(self):
        return self._command(cStopPolyScannerRun)

    def command_clear_poly_scanner_error(self):
        return self._command(cClearPolyScannerError)

    def command_set_poly_scanner_sos_delay(self):
        return self._command(cSetPolyScannerSOSDelay)

    def command_set_poly_scanner_fixed_sos_work(self):
        return self._command(cSetPolyScannerFixedSOSWork)

    def command_set_poly_scanner_sos_cor_value(self):
        return self._command(cSetPolyScannerSOSCorValue)

    def command_set_poly_scannner_y_cor(self):
        return self._command(cSetPolyScannerYCorPara)

    def command_set_polyscanner_pwm_para(self):
        return self._command(cSetPolyScannerPWMPara)

    def command_send_dsp_firmware(self):
        return self._command(cSendDspFirmware)

    def command_send_fpga_firmware(self):
        return self._command(cSendFPGAFirmware)

    def command_start_firmware_update(self):
        return self._command(cStartFirmwareUpdate)
