import xml.etree.ElementTree as ET

class JMDict:
    def __init__(self, xml_file):
        """Initialize JMDict with an XML file."""
        self.entries = self.load_entries(xml_file)

    def load_entries(self, xml_file):
        """Load all entries from the XML file into a dictionary of entries."""
        all_entries = {}
        tree = ET.parse(xml_file)
        root = tree.getroot()

        for entry in root.findall('entry'):
            word_key = self.get_keb(entry)
            if word_key not in all_entries:
                all_entries[word_key] = []

            entry_data = {
                'word': word_key,
                'reading': self.get_reb(entry),
                'tags': self.get_tags(entry),
                'meaning': self.get_meaning(entry),
                'notes': self.get_s_inf(entry),
            }
            all_entries[word_key].append(entry_data)

        return all_entries

    def get_keb(self, entry):
        """Get the key word (kanji)."""
        keb = entry.find('k_ele/keb')
        return keb.text if keb is not None else ''

    def get_reb(self, entry):
        """Get the reading (kana)."""
        reb = entry.find('r_ele/reb')
        return reb.text if reb is not None else ''

    def get_tags(self, entry):
        """Get tags (e.g., part of speech)."""
        tags = []
        for sense in entry.findall('sense'):
            pos_elements = sense.findall('pos')
            tags.extend([pos.text for pos in pos_elements if pos is not None])
        return tags

    def get_s_inf(self, entry):
        """Get tags (e.g., part of speech)."""
        s_inf = []
        for sense in entry.findall('sense'):
            s_inf_elements = sense.findall('s_inf')
            s_inf.extend([s_inf.text for s_inf in s_inf_elements if s_inf is not None])
        return s_inf

    def get_meaning(self, entry):
        """Extract and parse the meanings from structured content."""
        meanings = []
        for sense in entry.findall('sense'):
            for gloss in sense.findall('gloss'):
                meanings.append(gloss.text)
        return meanings

    def search_word(self, word):
        """Search for a word in the dictionary."""
        if word in self.entries:
            results = self.entries[word]
            # Sort by priority tags (e.g., common words first)
            results.sort(key=lambda x: self.tag_priority(x['tags']))
            return results
        return None

    def tag_priority(self, tags):
        """Define priority based on tags (common first, rare last)."""
        priority = 100  # Default to low priority
        if 'ichi' in tags:
            return 0  # Common
        elif 'news' in tags:
            return 1  # Used in news
        elif 'rare' in tags:
            return 99  # Rare
        return priority
    