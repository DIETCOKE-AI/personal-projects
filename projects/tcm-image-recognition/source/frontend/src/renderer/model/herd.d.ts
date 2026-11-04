interface SourceItem {
    id:number,
    standardName:string,
    characteristics:string,
    description:string,
    origin:string,
    latinName: string;
    medicinalParts: string;
    plantName:string;
    plantEName:string;
    priority:number;
    subclassName: string;
  }

  interface CardItem {
    id: number;
    // subclassName: string;
    imageUrl: string;
    // latinName: string;
    // medicinalParts: string;
    source:SourceItem[];
    isTrueHerb:number;
  }

  interface Material {
    thumbnail?: string;
    chineseName: string;
    latinName: string;
    standard: string;
    confidence?: string;
    main_class?: string;
    subclass?: string;
    main_confidence?: number;
    subclass_confidence?: number;
    filepath?:string;
    imagePath?:string
  }


  interface MaterialItem{
    id:string;
    chineseName:string;
    latinName:string;
    confidence:string;
    more:any[];
    source:any[];
    status:boolean;
    imageName:string;
    imagePath:string;
  }