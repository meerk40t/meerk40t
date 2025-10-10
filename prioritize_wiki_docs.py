#!/usr/bin/env python3
"""
Prioritize wiki pages for documentation improvement based on user impact and feature criticality.
"""


def prioritize_wiki_pages():
    """Categorize wiki pages by user impact and criticality."""

    # High priority - Core navigation and essential workflow
    critical_navigation = [
        "Online-Help-tree.md",  # Main project structure
        "Online-Help-devices.md",  # Device management
        "Online-Help-spooler.md",  # Job execution
        "Online-Help-jog.md",  # Basic movement
        "Online-Help-move.md",  # Position control
        "Online-Help-transform.md",  # Object manipulation
    ]

    # High priority - Device setup (users need this to get started)
    device_setup = [
        "Online-Help-grblconfig.md",
        "Online-Help-k40controller.md",
        "Online-Help-balorconfig.md",
        "Online-Help-moshiconfig.md",
        "Online-Help-newlyconfig.md",
        "Online-Help-grblhwconfig.md",
    ]

    # Medium priority - Operation configuration
    operation_config = [
        "Online-Help-operationproperty.md",
        "Online-Help-grbloperation.md",
        "Online-Help-k40operation.md",
        "Online-Help-baloroperation.md",
        "Online-Help-materialmanager.md",
        "Online-Help-preferences.md",
    ]

    # Medium priority - Design tools
    design_tools = [
        "Online-Help-alignment.md",
        "Online-Help-arrangement.md",
        "Online-Help-distribute.md",
        "Online-Help-placement.md",
        "Online-Help-position.md",
        "Online-Help-snap.md",
    ]

    # Lower priority - Specialized features
    specialized = [
        "Online-Help-camera.md",
        "Online-Help-simulate.md",
        "Online-Help-effects.md",
        "Online-Help-hatches.md",
        "Online-Help-wobbles.md",
        "Online-Help-warp.md",
        "Online-Help-templates.md",
        "Online-Help-testpattern.md",
        "Online-Help-vectortext.md",
        "Online-Help-textproperty.md",
        "Online-Help-imageproperty.md",
        "Online-Help-pathproperty.md",
        "Online-Help-opbranchproperty.md",
        "Online-Help-operationinfo.md",
        "Online-Help-threadinfo.md",
        "Online-Help-notes.md",
        "Online-Help-tips.md",
        "Online-Help-warning.md",
        "Online-Help-wordlist.md",
        "Online-Help-ribboneditor.md",
        "Online-Help-formatter.md",
        "Online-Help-defaultactions.md",
        "Online-Help-autoexec.md",
        "Online-Help-magnet.md",
        "Online-Help-drag.md",
        "Online-Help-pulse.md",
        "Online-Help-zmove.md",
        "Online-Help-keyhole.md",
        "Online-Help-imagesplit.md",
        "Online-Help-laserpanel.md",
    ]

    # Device controllers (medium priority - technical users)
    device_controllers = [
        "Online-Help-grblcontoller.md",
        "Online-Help-balorcontroller.md",
        "Online-Help-moshicontroller.md",
        "Online-Help-newlycontroller.md",
        "Online-Help-k40tcp.md",
    ]

    # Tools (lower priority - advanced features)
    tools = [
        "Online-Help-hinges.md",
        "Online-Help-kerf.md",
    ]

    categories = {
        "🚨 CRITICAL - Core Navigation & Workflow": critical_navigation,
        "🔧 HIGH - Device Setup": device_setup,
        "⚙️ MEDIUM - Operation Configuration": operation_config,
        "🎨 MEDIUM - Design Tools": design_tools,
        "🔌 MEDIUM - Device Controllers": device_controllers,
        "🛠️ LOWER - Specialized Features": specialized,
        "🔧 LOWER - Tools": tools,
    }

    return categories


def print_prioritization(categories):
    """Print the prioritized list with counts."""

    print("=== MeerK40t Wiki Documentation Prioritization ===\n")

    total_prioritized = 0
    total_pages = sum(len(pages) for pages in categories.values())
    for category, pages in categories.items():
        print(f"{category} ({len(pages)} pages):")
        for page in sorted(pages):
            print(f"   • {page}")
        print()
        total_prioritized += len(pages)

    print(
        f"- TOTAL: {total_prioritized} pages prioritized out of {total_pages} total wiki pages"
    )
    print()

    print("- IMPLEMENTATION PLAN:")
    print("   Phase 1 (Week 1-2): Complete CRITICAL and HIGH priority pages")
    print("   Phase 2 (Week 3-4): Complete MEDIUM priority pages")
    print("   Phase 3 (Week 5-6): Complete LOWER priority pages")
    print()
    print("- FOR EACH PAGE:")
    print(
        "   1. Replace '*Add a detailed description*' with comprehensive feature overview"
    )
    print("   2. Replace '*Step 1*', '*Step 2*', '*Step 3*' with actual usage steps")
    print("   3. Replace '*Add technical information*' with implementation details")
    print("   4. Add screenshots for visual features")
    print("   5. Update related topics links")
    print("   6. Test documentation with new users")


if __name__ == "__main__":
    categories = prioritize_wiki_pages()
    print_prioritization(categories)
